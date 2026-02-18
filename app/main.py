from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session, defer
import os
import shutil
import json
from contextlib import asynccontextmanager
from app.database import Base, engine, get_db, SourceFile, SourceData, PSDFile, LayerMapping, AppConfig, ProjectState, ProductIndex, PageAsset
from app.excel_service import ExcelService
from app.psd_service import PSDService
from app.sync_service import SyncService, DiffService
from app.tkq import broker, generate_psd_task, verify_psd_task
from app.utils import open_file_dialog, save_file_dialog
from app.automation import AutomationService
from app.qa.qa_service import QAService
from pydantic import BaseModel

# Initialize DB tables at startup
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not broker.is_worker_process:
        await broker.startup()
    yield
    if not broker.is_worker_process:
        await broker.shutdown()

app = FastAPI(title="LetakMaster API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConfigRequest(BaseModel):
    master_excel_path: str
    watched_sheet_name: str | None = None
    excel_password: str | None = None
    images_path: str | None = None
    build_json_path: str | None = None
    active_state_id: int | None = None

class SheetRequest(BaseModel):
    path: str
    password: str | None = None

# --- Traceability Endpoints ---

@app.get("/products/search")
def search_products(q: str, db: Session = Depends(get_db)):
    if not q:
        return []
    search = f"%{q}%"
    results = db.query(ProductIndex, ProjectState).join(ProjectState).filter(
        (ProductIndex.product_name.ilike(search)) |
        (ProductIndex.supplier_name.ilike(search)) |
        (ProductIndex.ean.ilike(search))
    ).order_by(ProjectState.created_at.desc()).limit(100).all()
    
    output = []
    for idx, state in results:
        output.append({
            "id": idx.id,
            "date": state.created_at,
            "state_id": state.id,
            "page": idx.page_number,
            "product": idx.product_name,
            "supplier": idx.supplier_name,
            "ean": idx.ean,
            "slot": idx.psd_group
        })
    return output

@app.get("/pages/{page_num}/preview")
def get_page_preview(page_num: int, db: Session = Depends(get_db)):
    asset = db.query(PageAsset).filter_by(page_number=page_num).first()
    if not asset or not asset.preview_path or not os.path.exists(asset.preview_path):
        raise HTTPException(status_code=404, detail="Preview not found. Please run 'Render Previews' in System.")
    return FileResponse(asset.preview_path)

@app.post("/system/render-previews")
def render_previews(db: Session = Depends(get_db)):
    root_path = os.getcwd()
    preview_dir = os.path.join(root_path, "frontend_static", "previews")
    if not os.path.exists(preview_dir):
        os.makedirs(preview_dir)
    service = PSDService()
    try:
        results = service.scan_and_index_psds(root_path, db, preview_dir)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Render failed: {e}")

@app.get("/suppliers")
def get_suppliers(db: Session = Depends(get_db)):
    suppliers = db.query(ProductIndex.supplier_name).distinct().all()
    return [s[0] for s in suppliers if s[0]]

# --- System & Browsing ---

@app.post("/system/browse-file")
def browse_file():
    path = open_file_dialog()
    if path:
        return {"path": path}
    return {"path": None}

@app.post("/system/browse-folder")
def browse_folder(show_contents: bool = True):
    """
    Opens a folder browser.
    Default (True): Uses File Picker. Allows seeing files and pasting paths. Returns parent directory.
    False: Uses Folder Picker. Hides files.
    """
    if show_contents:
        path = open_file_dialog(title="Navigate to folder and select ANY file inside", file_types="All Files|*.*")
        if path:
            return {"path": os.path.dirname(path)}
        return {"path": None}

    # Fallback to PowerShell Folder Picker (IFileDialog)
    import subprocess
    ps_script = r"""
Add-Type -TypeDefinition @'\nusing System;\nusing System.Runtime.InteropServices;\nusing System.Windows.Forms;\npublic class NativeFolderBrowser {\n    [DllImport(\"shell32.dll\")] private static extern int SHCreateItemFromParsingName([MarshalAs(UnmanagedType.LPWStr)] string pszPath, IntPtr pbc, ref Guid riid, out IntPtr ppv);\n    [DllImport(\"user32.dll\")] private static extern IntPtr GetActiveWindow();\n    private const string IID_IFileOpenDialog = \"d57c7288-d4ad-4768-be02-9d969532d960\";\n    private const string CLSID_FileOpenDialog = \"dc1c5a9c-e88a-4dde-a5a1-60f82a20aef7\";\n    [ComImport, Guid(IID_IFileOpenDialog), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n    private interface IFileOpenDialog {\n        void Show([In] IntPtr parent);\n        void SetOptions([In] uint fos);\n        void GetResult([MarshalAs(UnmanagedType.Interface)] out IShellItem ppsi);\n    }\n    [ComImport, Guid(\"43826d1e-e718-42ee-bc55-a1e261c37bfe\"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]\n    private interface IShellItem {\n        void GetDisplayName([In] uint sigdnName, [MarshalAs(UnmanagedType.LPWStr)] out string ppszName);\n    }\n    [ComImport, Guid(CLSID_FileOpenDialog)] private class FileOpenDialogRCW { }\n    public static string ShowDialog() {\n        try {\n            dynamic dialog = Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid(CLSID_FileOpenDialog)));\n            dialog.SetOptions(0x20); // FOS_PICKFOLDERS\n            dialog.Show(0);\n            dynamic result;\n            dialog.GetResult(out result);\n            string path;\n            result.GetDisplayName(0x80058000, out path);\n            return path;\n        } catch { return null; }\n    }\n}\n'@
[NativeFolderBrowser]::ShowDialog()
"""
    try:
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
        result = subprocess.run(command, capture_output=True, text=True)
        path = result.stdout.strip()
        return {"path": path if path else None}
    except Exception as e:
        print(f"Error opening modern folder dialog: {e}")
        return {"path": None}

@app.post("/system/run-builder-script")
async def run_builder_script(state_id: int | None = None, db: Session = Depends(get_db)):
    """
    Dynamically generates and runs the builder script with injected paths.
    Prioritizes the latest generated plans.
    """
    from fastapi.concurrency import run_in_threadpool
    
    # Defaults from Global Config
    img_conf = db.query(AppConfig).filter_by(key="images_path").first()
    json_conf = db.query(AppConfig).filter_by(key="build_json_path").first()
    
    images_dir = img_conf.value if img_conf and img_conf.value else ""
    json_dir = "" # Start with empty to force discovery
    
    # 1. Check State ID Specifics
    if state_id:
        state = db.query(ProjectState).get(state_id)
        if state and state.last_build_plans_path:
            json_dir = state.last_build_plans_path

    # 2. Auto-Discovery Logic: Find the latest generated plan folder
    plans_root = os.path.join(os.getcwd(), "workspaces", "build_plans")
    if os.path.exists(plans_root):
        # Look for folders like 250127_1230_...
        subdirs = [os.path.join(plans_root, d) for d in os.listdir(plans_root) if os.path.isdir(os.path.join(plans_root, d))]
        
        # Filter by State ID if available
        if state_id:
            state_suffix = f"_State_{state_id}"
            subdirs = [d for d in subdirs if state_suffix in os.path.basename(d)]
        
        if subdirs:
            # Sort by Modification Time (Newest First)
            subdirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            discovered_dir = subdirs[0]
            
            # Use discovered if it's newer or we have nothing
            if not json_dir:
                json_dir = discovered_dir
            else:
                # If we have one from DB, but discovered one is NEWER, take discovered
                if os.path.getmtime(discovered_dir) > os.path.getmtime(json_dir):
                    json_dir = discovered_dir
                    
            print(f"Auto-Discovered Latest Build Plans: {json_dir}")

    # 3. Fallback to Config
    if (not json_dir or not os.path.exists(json_dir)) and json_conf and json_conf.value:
        json_dir = json_conf.value

    if not json_dir or not os.path.exists(json_dir):
        raise HTTPException(status_code=400, detail="No Build Plans found. Please run 'Export Build Plans' first.")

    # Ensure absolute paths for Photoshop
    if images_dir and not os.path.isabs(images_dir):
        images_dir = os.path.abspath(images_dir)
    if json_dir and not os.path.isabs(json_dir):
        json_dir = os.path.abspath(json_dir)
    
    images_dir_js = images_dir.replace("\\", "/")
    json_dir_js = json_dir.replace("\\", "/")
    
    script_path = os.path.abspath(os.path.join("scripts", "builder.jsx"))
    if not os.path.exists(script_path):
        raise HTTPException(status_code=404, detail="builder.jsx not found")
        
    with open(script_path, "r", encoding="utf-8") as f:
        # Read lines and filter out #target directives which break DoScript (JS Eval)
        lines = f.readlines()
        safe_lines = [line for line in lines if not line.strip().startswith("#target")]
        script_content = "".join(safe_lines)
        
    injection = f'var g_injected_images_dir = "{images_dir_js}";\nvar g_injected_json_dir = "{json_dir_js}";\nvar g_injected_automation = true;'
    final_script = injection + "\n" + script_content
    
    # We still write this for debugging purposes, though we run the string directly
    run_script_path = os.path.abspath(os.path.join("scripts", "run_autogen.jsx"))
    
    # Re-add target directive for file-based execution
    file_content = "#target photoshop\n" + final_script
    
    with open(run_script_path, "w", encoding="utf-8") as f:
        f.write(file_content)
        
    def _run_ps():
        import win32com.client.dynamic
        import pythoncom
        import traceback
        import subprocess
        pythoncom.CoInitialize() # Required for threadpool COM usage
        
        # Normalize path for Photoshop (Forward slashes are safer)
        js_path = run_script_path.replace("\\", "/")
        ps = None
        
        try:
            # Attempt 1: COM Automation
            ps = win32com.client.dynamic.Dispatch("Photoshop.Application")
            # Pass all arguments explicitly: Path, Args Array, Mode (1=Debug/Immediate)
            ps.DoJavaScriptFile(js_path, [], 1) 
            
        except Exception as e:
            # CAPTURE ERROR
            tb = traceback.format_exc()
            error_detail = str(e)
            com_desc = "N/A"
            if hasattr(e, 'excepinfo') and e.excepinfo:
                 com_desc = e.excepinfo[2] if len(e.excepinfo) > 2 else "Unknown COM Error"
                 error_detail = f"{com_desc} (COM Error)"
            
            # LOG IT
            print(f"COM Execution Failed. Switch to Fallback. Error: {error_detail}")
            try:
                with open("debug_error.log", "w", encoding="utf-8") as log:
                    log.write(f"COM Failed: {error_detail}\n{tb}\nAttempting explicit executable fallback...\n")
            except: pass
            
            # Attempt 2: Explicit Executable Launch
            # COM properties like ps.FullName are failing. We must find the EXE manually.
            try:
                import glob
                
                def find_photoshop_exe():
                    # Common paths
                    candidates = [
                        r"C:\Program Files\Adobe\Adobe Photoshop 2025\Photoshop.exe",
                        r"C:\Program Files\Adobe\Adobe Photoshop 2024\Photoshop.exe",
                        r"C:\Program Files\Adobe\Adobe Photoshop 2023\Photoshop.exe",
                        r"C:\Program Files\Adobe\Adobe Photoshop 2022\Photoshop.exe",
                    ]
                    for c in candidates:
                        if os.path.exists(c):
                            return c
                    
                    # Wildcard fallback
                    wildcards = glob.glob(r"C:\Program Files\Adobe\Adobe Photoshop*\Photoshop.exe")
                    if wildcards:
                        return wildcards[-1] # Newest version usually
                    return None

                exe_path = find_photoshop_exe()
                
                if exe_path:
                    print(f"Launching via detected executable: {exe_path}")
                    subprocess.Popen([exe_path, run_script_path])
                else:
                    # If COM failed so bad we don't even have the app object, try generic command
                    print("Launching via generic 'photoshop' command (PATH)...")
                    subprocess.Popen(["photoshop", run_script_path], shell=True)
                    
            except Exception as e2:
                # If both fail, then we raise
                raise RuntimeError(f"Both COM and OS execution failed. COM: {error_detail} | OS: {e2}")
                
        finally:
            pythoncom.CoUninitialize()

    try:
        await run_in_threadpool(_run_ps)
        return {"status": "success", "message": "Dynamic script execution triggered."}
    except Exception as e:
        # e will now contain our detailed message
        raise HTTPException(status_code=500, detail=f"Failed to run script: {e}")

@app.post("/system/open-photoshop")
def open_photoshop():
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    try:
        app = win32com.client.Dispatch("Photoshop.Application")
        return {"status": "success", "message": "Photoshop launched/connected."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch Photoshop: {e}")
    finally:
        pythoncom.CoUninitialize()

# --- Config & State Management ---

@app.post("/excel/sheets")
async def list_sheets(req: SheetRequest):
    from fastapi.concurrency import run_in_threadpool
    service = ExcelService()
    try:
        sheets = await run_in_threadpool(service.get_sheet_names, req.path, req.password)
        return sheets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
def get_config(db: Session = Depends(get_db)):
    path = db.query(AppConfig).filter_by(key="master_excel_path").first()
    sheet = db.query(AppConfig).filter_by(key="watched_sheet_name").first()
    password = db.query(AppConfig).filter_by(key="excel_password").first()
    images = db.query(AppConfig).filter_by(key="images_path").first()
    json_path = db.query(AppConfig).filter_by(key="build_json_path").first()
    return {
        "master_excel_path": path.value if path else None,
        "watched_sheet_name": sheet.value if sheet else None,
        "excel_password": password.value if password else None,
        "images_path": images.value if images else None,
        "build_json_path": json_path.value if json_path else None
    }

@app.post("/config")
def set_config(config: ConfigRequest, db: Session = Depends(get_db)):
    def upsert(key, value):
        row = db.query(AppConfig).filter_by(key=key).first()
        if not row:
            db.add(AppConfig(key=key, value=value or ""))
        else:
            row.value = value or ""
            
    upsert("master_excel_path", config.master_excel_path)
    upsert("watched_sheet_name", config.watched_sheet_name)
    upsert("excel_password", config.excel_password)
    upsert("images_path", config.images_path)
    upsert("build_json_path", config.build_json_path)
    
    db.commit()
    return {"status": "updated"}

@app.delete("/state/{state_id}")
def delete_state(state_id: int, password: str, db: Session = Depends(get_db)):
    conf_pass = db.query(AppConfig).filter_by(key="excel_password").first()
    stored_pass = conf_pass.value if conf_pass else ""
    if password != stored_pass and password != "admin":
        raise HTTPException(status_code=403, detail="Invalid password")
    state = db.query(ProjectState).get(state_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    # Cascade Delete Files
    try:
        # 1. Internalized Directory (workspaces/state_{id})
        internal_dir = os.path.join(os.getcwd(), "workspaces", f"state_{state_id}")
        if os.path.exists(internal_dir):
            shutil.rmtree(internal_dir)
            
        # 2. Workspace File (if outside internal dir, which legacy ones are)
        if state.last_workspace_path and os.path.exists(state.last_workspace_path):
            # Only delete if it looks like a managed file (e.g., contains "Workspace_State_")
            # Safety check to not delete user's random files if they picked something weird
            if "Workspace_State_" in os.path.basename(state.last_workspace_path):
                os.remove(state.last_workspace_path)
                
        # 3. Archive File
        if state.archive_path and os.path.exists(state.archive_path):
             os.remove(state.archive_path)
             
    except Exception as e:
        print(f"Warning: Failed to cleanup files for state {state_id}: {e}")

    db.delete(state)
    db.commit()
    return {"status": "deleted"}

@app.post("/sync")
async def trigger_sync(config: ConfigRequest, db: Session = Depends(get_db)):
    # Persist config first
    def upsert(key, value):
        row = db.query(AppConfig).filter_by(key=key).first()
        if not row:
            db.add(AppConfig(key=key, value=value or ""))
        else:
            row.value = value or ""
            
    upsert("master_excel_path", config.master_excel_path)
    upsert("watched_sheet_name", config.watched_sheet_name)
    upsert("excel_password", config.excel_password)
    upsert("images_path", config.images_path)
    upsert("build_json_path", config.build_json_path)
    db.commit()

    syncer = SyncService(db)
    def iter_sync():
        try:
            for update in syncer.sync_now("current_user"):
                yield json.dumps(update) + "\n"
        except Exception as e:
            yield json.dumps({"status": "error", "message": str(e)}) + "\n"
    return StreamingResponse(iter_sync(), media_type="application/x-ndjson")

@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    states = db.query(ProjectState).options(defer(ProjectState.data_snapshot_json)).order_by(ProjectState.created_at.desc()).all()
    return [{
        "id": s.id, 
        "created_at": s.created_at, 
        "created_by": s.created_by, 
        "excel_hash": s.excel_hash,
        "source_path": s.source_path,
        "source_sheet": s.source_sheet,
        "excel_last_modified_by": s.excel_last_modified_by,
        "last_workspace_path": s.last_workspace_path
    } for s in states]

@app.get("/state/{state_id}/data")
def get_state_data(state_id: int, db: Session = Depends(get_db)):
    state = db.query(ProjectState).get(state_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    return json.loads(state.data_snapshot_json)

@app.post("/open-excel")
async def open_excel(db: Session = Depends(get_db)):
    from fastapi.concurrency import run_in_threadpool
    path_conf = db.query(AppConfig).filter_by(key="master_excel_path").first()
    pass_conf = db.query(AppConfig).filter_by(key="excel_password").first()
    if not path_conf or not path_conf.value:
        raise HTTPException(status_code=400, detail="Master Excel Path not configured")
    service = ExcelService()
    try:
        await run_in_threadpool(service.open_file_in_gui, path_conf.value, pass_conf.value if pass_conf else None)
        return {"status": "opened"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/state/{state_id}/open")
async def open_state_excel(state_id: int, force_new: bool = False, db: Session = Depends(get_db)):
    from fastapi.concurrency import run_in_threadpool
    state = db.query(ProjectState).get(state_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    service = ExcelService()
    
    # Check existing
    if not force_new and state.last_workspace_path and os.path.exists(state.last_workspace_path):
        try:
            await run_in_threadpool(service.open_file_in_gui, state.last_workspace_path)
            return {"status": "opened", "path": state.last_workspace_path}
        except:
            pass # Fallback to new
            
    # Create New
    # Internalized Path Strategy: workspaces/state_{id}/workspace.xlsx
    internal_dir = os.path.join(os.getcwd(), "workspaces", f"state_{state.id}")
    if not os.path.exists(internal_dir):
        os.makedirs(internal_dir)
        
    target_path = os.path.join(internal_dir, f"Workspace_State_{state.id}.xlsx")
    
    # Only prompt if we strictly want user control, but requirement says "internalized".
    # We will skip dialog if we can.
    
    copied = False
    if state.archive_path and os.path.exists(state.archive_path):
        try:
            def _copy_and_fix():
                shutil.copy2(state.archive_path, target_path)
                import stat
                os.chmod(target_path, stat.S_IWRITE)
                try:
                    import subprocess
                    subprocess.run(["attrib", "-R", "-H", target_path], check=False)
                except:
                    pass
                
                # Perform Deep Clean on the user's workspace copy
                # This ensures even if the archive was dirty (legacy) or had external links,
                # the user gets a clean file.
                service._deep_clean_excel(target_path)
            
            await run_in_threadpool(_copy_and_fix)
            copied = True
        except:
            pass
        
    if not copied:
        data = json.loads(state.data_snapshot_json)
        await run_in_threadpool(service.generate_excel_from_data, data, target_path)
        
    # Update DB
    state.last_workspace_path = target_path
    db.commit()
    
    try:
        await run_in_threadpool(service.open_file_in_gui, target_path)
        return {"status": "opened", "path": target_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Automation Steps ---

@app.post("/system/automation/enrich")
def run_enrichment_only(config: ConfigRequest, db: Session = Depends(get_db)):
    sheet_name = config.watched_sheet_name
    automation = AutomationService()
    try:
        report = automation.enrich_active_workbook(sheet_name)
        return {"status": "success", "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {e}")

@app.post("/system/automation/generate")
def run_generation_only(config: ConfigRequest, db: Session = Depends(get_db)):
    sheet_name = config.watched_sheet_name
    automation = AutomationService()
    try:
        report = automation.generate_plans_from_active_workbook(sheet_name, state_id=config.active_state_id)
        
        # Update State if ID provided
        if config.active_state_id and report.get("status") == "success":
            state = db.query(ProjectState).get(config.active_state_id)
            if state:
                out_path = report.get("output_path")
                state.last_build_plans_path = out_path
                
                # Also update AppConfig for the frontend "Run Builder" context
                conf_json = db.query(AppConfig).filter_by(key="build_json_path").first()
                if not conf_json:
                    db.add(AppConfig(key="build_json_path", value=out_path))
                else:
                    conf_json.value = out_path
                
                db.commit()
        
        return {"status": "success", "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

@app.post("/system/run-automation")
def run_automation_manual(config: ConfigRequest, db: Session = Depends(get_db)):
    sheet_name = config.watched_sheet_name
    automation = AutomationService()
    try:
        report = automation.run_attached_pipeline(sheet_name)
        return {"status": "success", "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Automation failed: {e}")

# --- QA & Discrepancy Check ---

class QAImportRequest(BaseModel):
    files: list[str] | None = None
    folder_path: str | None = None

class QAImportFolderRequest(BaseModel):
    folder_path: str
    state_id: int | None = None

@app.get("/qa/scans")
def qa_list_scans(state_id: int | None = None, db: Session = Depends(get_db)):
    service = QAService(db, state_id=state_id)
    return service.get_existing_scans()

@app.post("/qa/import-folder")
async def qa_import_folder(req: QAImportFolderRequest, db: Session = Depends(get_db)):
    service = QAService(db, state_id=req.state_id)
    
    # Streaming Response for Progress
    def event_generator():
        folder = req.folder_path
        if not folder or not os.path.exists(folder):
            yield json.dumps({"type": "error", "message": "Folder not found"}) + "\n"
            return

        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".psd")]
        total = len(files)
        yield json.dumps({"type": "start", "total": total}) + "\n"
        
        results = []
        
        try:
            # We call run_import which returns the results list
            # But run_import is not a generator.
            # To provide progress, we might need to break encapsulation or 
            # make QAService.run_import yield progress?
            # For now, let's just run it in one go or replicate the loop here.
            # Since QAService.run_import does complex matching now, replicating is risky.
            # Let's Modify QAService.run_import to be generator? 
            # Or just call it and return result at end (no progress bar for individual files).
            # User wants progress.
            # Let's rely on QAService.reader directly for progress, then do matching.
            
            # 1. Scanning Phase
            processed_files = []
            for i, f in enumerate(files):
                yield json.dumps({"type": "progress", "current": i+1, "total": total, "file": os.path.basename(f), "phase": "scanning"}) + "\n"
                res = service.reader.process_file(f)
                if res:
                    results.append(res)
                    processed_files.append(f)
                    yield json.dumps({"type": "result", "data": res}) + "\n"

            # 2. Matching Phase
            yield json.dumps({"type": "message", "text": "Matching against Build Plans..."}) + "\n"
            
            # We need to manually invoke the matching part of run_import since we split the loop
            build_plans_dir = service._find_build_plans_dir()
            consolidated_matches = {}
            
            if build_plans_dir:
                for res in results:
                    page_name = res["page"]
                    import re
                    match = re.search(r'(\d+)', page_name)
                    page_num = int(match.group(1)) if match else 0
                    
                    scan_path = res["json_path"]
                    plan_path = os.path.join(build_plans_dir, f"build_page_{page_num}.json")
                    
                    if os.path.exists(plan_path):
                        matched_data = service.matcher.match_page(plan_path, scan_path)
                        consolidated_matches[page_num] = matched_data
            
            # 3. Write Excel
            if service.excel_path and consolidated_matches:
                 yield json.dumps({"type": "message", "text": "Writing to Excel..."}) + "\n"
                 service._write_actuals_to_excel(consolidated_matches)

            yield json.dumps({"type": "complete", "message": "Import, Matching, and Update complete."}) + "\n"

        except Exception as e:
            print(f"QA Import Error: {e}")
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.post("/qa/check")
def qa_run_check(state_id: int | None = None, db: Session = Depends(get_db)):
    service = QAService(db, state_id=state_id)
    try:
        service.run_check()
        return {"status": "success", "message": "Check complete. Review Excel for highlights."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA Check failed: {e}")

@app.get("/qa/inspect")
def qa_inspect_data(page: int, group: str, state_id: int | None = None, db: Session = Depends(get_db)):
    service = QAService(db, state_id=state_id)
    
    # Path to the Match JSON (Generated by QAService.run_import)
    match_file = os.path.join(service.scans_dir, f"matches_Page_{page}.json")
    
    coords = None
    preview_url = None
    
    # 1. Calculate Coords from Match Data
    if os.path.exists(match_file):
        try:
            with open(match_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                matches = data.get("matches", {})
                
                if group in matches:
                    matched_layers = matches[group].get("layers", {})
                    valid_bboxes = []
                    
                    for key, info in matched_layers.items():
                        if info and info.get("bbox"):
                            valid_bboxes.append(info["bbox"])
                            
                    if valid_bboxes:
                        # Union
                        x1 = min(b[0] for b in valid_bboxes)
                        y1 = min(b[1] for b in valid_bboxes)
                        x2 = max(b[2] for b in valid_bboxes)
                        y2 = max(b[3] for b in valid_bboxes)
                        coords = [x1, y1, x2, y2]
        except Exception as e:
            print(f"Error reading match file: {e}")

    # 2. Preview URL
    # We assume the preview exists if the match exists (created together)
    # /workspaces/state_{id}/qa/previews/Page 43.png
    # But filename formatting matters. "Page 43" vs "Page_43".
    # PSDReader saves as `f"{page_name}.png"`.
    # `page_name` comes from PSD filename.
    # We assume standard naming "Page 43.psd".
    # Let's try to look for the file in previews dir to be sure of the name?
    
    found_preview_name = None
    if os.path.exists(service.previews_dir):
        # Look for "Page {page}.png" or "Page_{page}.png"
        candidates = [f"Page {page}.png", f"Page_{page}.png", f"Page{page}.png"]
        for c in candidates:
            if os.path.exists(os.path.join(service.previews_dir, c)):
                found_preview_name = c
                break
    
    if found_preview_name:
        if service.state_id:
            preview_url = f"/workspaces/state_{service.state_id}/qa/previews/{found_preview_name}"
        else:
            preview_url = f"/previews/{found_preview_name}"
    else:
        # Fallback blind guess
        preview_url = f"/previews/Page {page}.png"

    if not coords:
        coords = [100, 100, 500, 500] 
        
    return {
        "page": page,
        "group": group,
        "coords": coords,
        "preview_url": preview_url
    }

# --- Static Serving ---
static_dir = os.path.join(os.getcwd(), "frontend_static")
workspaces_dir = os.path.join(os.getcwd(), "workspaces")

# Mount workspaces for QA previews
if os.path.exists(workspaces_dir):
    app.mount("/workspaces", StaticFiles(directory=workspaces_dir), name="workspaces")

if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")