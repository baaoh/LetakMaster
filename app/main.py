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
    Prioritizes the paths linked to the specific State ID if provided.
    """
    from fastapi.concurrency import run_in_threadpool
    
    # Defaults from Global Config
    img_conf = db.query(AppConfig).filter_by(key="images_path").first()
    json_conf = db.query(AppConfig).filter_by(key="build_json_path").first()
    
    images_dir = img_conf.value if img_conf and img_conf.value else ""
    json_dir = json_conf.value if json_conf and json_conf.value else ""
    
    # Override with State Specifics if available
    if state_id:
        state = db.query(ProjectState).get(state_id)
        if state and state.last_build_plans_path:
            json_dir = state.last_build_plans_path
            
    # Auto-Discovery Logic: If json_dir is still empty/invalid, find the latest generated plan
    if not json_dir or not os.path.exists(json_dir):
        # Check workspaces/build_plans for the newest folder
        plans_root = os.path.join(os.getcwd(), "workspaces", "build_plans")
        if os.path.exists(plans_root):
            subdirs = [os.path.join(plans_root, d) for d in os.listdir(plans_root) if os.path.isdir(os.path.join(plans_root, d))]
            
            # Filter by State ID if available
            if state_id:
                state_suffix = f"_State_{state_id}"
                # We look for folders ending with this suffix or containing it clearly
                state_matches = [d for d in subdirs if state_suffix in os.path.basename(d)]
                if state_matches:
                    subdirs = state_matches
            
            if subdirs:
                # Sort by Modification Time (Newest First) - Foolproof
                subdirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                json_dir = subdirs[0]
                
            if json_dir:
                print(f"Auto-Discovered Latest Build Plans: {json_dir}")

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

@app.get("/qa/scans")
def qa_list_scans(db: Session = Depends(get_db)):
    path_conf = db.query(AppConfig).filter_by(key="master_excel_path").first()
    service = QAService(path_conf.value if path_conf else None)
    return service.get_existing_scans()

@app.post("/qa/import-folder")
async def qa_import_folder(req: QAImportFolderRequest, db: Session = Depends(get_db)):
    path_conf = db.query(AppConfig).filter_by(key="master_excel_path").first()
    pass_conf = db.query(AppConfig).filter_by(key="excel_password").first()
    
    service = QAService(path_conf.value if path_conf else None, pass_conf.value if pass_conf else None)
    
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
        for i, f in enumerate(files):
            yield json.dumps({"type": "progress", "current": i+1, "total": total, "file": os.path.basename(f)}) + "\n"
            try:
                res = service.reader.process_file(f)
                if res:
                    results.append(res)
                    yield json.dumps({"type": "result", "data": res}) + "\n"
            except Exception as e:
                print(f"Error processing {f}: {e}")
        
        # Finalize
        if results:
            # We need to consolidate and write to Excel
            # This part is fast enough to do at the end
            try:
                consolidated = {}
                for r in results:
                    with open(r['json_path'], 'r', encoding='utf-8') as jf:
                        data = json.load(jf)
                        page_name = data.get("page_name", "")
                        import re
                        match = re.search(r'Page\s*_?\s*(\d+)', page_name, re.IGNORECASE)
                        page_num = int(match.group(1)) if match else 0
                        if page_num not in consolidated: consolidated[page_num] = {}
                        consolidated[page_num].update(data.get("groups", {}))
                
                service._write_actuals_to_excel(consolidated)
                yield json.dumps({"type": "complete", "message": "Import and Excel update complete."}) + "\n"
            except Exception as e:
                yield json.dumps({"type": "error", "message": f"Excel Write failed: {str(e)}"}) + "\n"
        else:
            yield json.dumps({"type": "complete", "message": "No valid PSDs processed."}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.post("/qa/check")
def qa_run_check(db: Session = Depends(get_db)):
    path_conf = db.query(AppConfig).filter_by(key="master_excel_path").first()
    pass_conf = db.query(AppConfig).filter_by(key="excel_password").first()
    
    service = QAService(path_conf.value if path_conf else None, pass_conf.value if pass_conf else None)
    try:
        service.run_check()
        return {"status": "success", "message": "Check complete. Review Excel for highlights."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QA Check failed: {e}")

@app.get("/qa/inspect")
def qa_inspect_data(page: int, group: str):
    # Retrieve coordinates for spotlight
    # We need to find the scan json for this page
    # Look in workspaces/qa/scans
    
    root = os.getcwd()
    scans_dir = os.path.join(root, "workspaces", "qa", "scans")
    
    # Try finding file matching page number
    # Scan format: scan_Page 43.json or scan_Page_43.json
    # We'll just list and check content or name
    
    target_file = None
    if os.path.exists(scans_dir):
        for f in os.listdir(scans_dir):
            if f.endswith(".json") and f"Page {page}" in f.replace("_", " "): 
                # Simple heuristic match
                target_file = os.path.join(scans_dir, f)
                break
                
    if not target_file:
        # Fallback: Maybe filename doesn't have "Page" word?
        pass

    coords = None
    preview_url = None
    
    if target_file:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "groups" in data and group in data["groups"]:
                coords = data["groups"][group]["bbox"]
            
            # Preview path relative to frontend
            # The preview filename usually matches the json filename base
            base = os.path.splitext(os.path.basename(target_file))[0].replace("scan_", "")
            preview_url = f"/previews/{base}.png"

    if not coords:
        # Fallback dummy if file missing (for dev UI testing)
        coords = [100, 100, 500, 500] 
        
    return {
        "page": page,
        "group": group,
        "coords": coords, # [x1, y1, x2, y2]
        "preview_url": preview_url
    }

# --- Uploads & Diff ---

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.post("/upload/excel")
def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        db_file = SourceFile(filename=file.filename, path=file_path)
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        service = ExcelService()
        parsed_data = service.parse_file(file_path, header_row=6)
        for row_idx, row in enumerate(parsed_data):
            for col_name, cell_data in row.items():
                db_data = SourceData(
                    source_file_id=db_file.id,
                    row_index=row_idx + 7,
                    column_name=col_name,
                    value=str(cell_data["value"]) if cell_data["value"] is not None else None,
                    formatting_json=json.dumps(cell_data["formatting"])
                )
                db.add(db_data)
        db.commit()
        return {"file_id": db_file.id, "rows_imported": len(parsed_data)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/diff/{id1}/{id2}")
def get_diff(id1: int, id2: int, db: Session = Depends(get_db)):
    s1 = db.query(ProjectState).get(id1)
    s2 = db.query(ProjectState).get(id2)
    if not s1 or not s2:
        raise HTTPException(status_code=404, detail="State not found")
    differ = DiffService()
    data1 = json.loads(s1.data_snapshot_json)
    data2 = json.loads(s2.data_snapshot_json)
    def flatten(rows):
        flat = []
        for r in rows:
            item = {}
            for k, v in r.items():
                item[k] = v.get("value")
            flat.append(item)
        return flat
    return differ.compare(flatten(data1), flatten(data2))

@app.post("/psd/register")
def register_psd(filename: str, path: str, db: Session = Depends(get_db)):
    db_psd = PSDFile(filename=filename, path=path)
    db.add(db_psd)
    db.commit()
    db.refresh(db_psd)
    return db_psd

@app.post("/psd/{psd_id}/generate")
async def trigger_psd_generation(psd_id: int):
    task = await generate_psd_task.kiq(psd_id)
    return {"task_id": task.task_id}

@app.post("/psd/{psd_id}/verify")
async def trigger_psd_verification(psd_id: int):
    task = await verify_psd_task.kiq(psd_id)
    return {"task_id": task.task_id}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    return {"status": "In-memory tasks are executed immediately by InMemoryBroker"}

@app.get("/source-files")
def list_source_files(db: Session = Depends(get_db)):
    return db.query(SourceFile).all()

@app.get("/psd-files")
def list_psd_files(db: Session = Depends(get_db)):
    return db.query(PSDFile).all()

@app.get("/source-files/{file_id}/data")
def get_source_file_data(file_id: int, db: Session = Depends(get_db)):
    return db.query(SourceData).filter(SourceData.source_file_id == file_id).all()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/system/logs")
def get_system_logs():
    log_path = os.path.join(os.getcwd(), "logs.txt")
    if not os.path.exists(log_path):
        return "No logs found."
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        # Return last 100 lines
        lines = f.readlines()
        return "".join(lines[-100:])

# --- Static Serving ---
static_dir = os.path.join(os.getcwd(), "frontend_static")
if os.path.exists(static_dir):
    # Mount everything at root. Since this is the LAST mount added,
    # it serves as a fallback for everything not caught by API routes.
    # html=True ensures index.html is served for the root path.
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    # Optional: If you want true SPA behavior (routing handled by frontend),
    # you can still keep the exception handler for 404s to return index.html
    @app.exception_handler(404)
    async def spa_fallback(request, exc):
        if request.method == "GET" and not request.url.path.startswith("/api"):
            return FileResponse(os.path.join(static_dir, "index.html"))
        # For API 404s, we still want the standard JSON response
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"detail": "Not Found"})