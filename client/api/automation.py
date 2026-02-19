from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from client.agent.sync_manager import SyncManager
from client.automation.excel_agent import ExcelAgent
from client.automation.designer_service import DesignerService
import subprocess

router = APIRouter(prefix="/automation", tags=["Automation"])

class SyncTrigger(BaseModel):
    project_id: int
    excel_path: str
    sheet_name: str
    password: Optional[str] = None

class SheetListRequest(BaseModel):
    excel_path: str
    password: Optional[str] = None

class OpenExcelRequest(BaseModel):
    excel_path: str
    sheet_name: Optional[str] = None
    password: Optional[str] = None

class RunBuilderRequest(BaseModel):
    images_path: Optional[str] = None

@router.post("/browse-file")
async def browse_excel_file():
    """
    Opens a native Windows file dialog via PowerShell.
    """
    cmd = (
        "powershell -NoProfile -Command \""
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$f = New-Object System.Windows.Forms.OpenFileDialog; "
        "$f.Filter = 'Excel Files (*.xls, *.xlsx, *.xlsm)|*.xls;*.xlsx;*.xlsm'; "
        "$f.ShowDialog() | Out-Null; "
        "$f.FileName\""
    )
    try:
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        return {"path": output.replace("\\", "/")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Browser Error: {str(e)}")

@router.post("/open-excel")
async def open_excel_workspace(req: OpenExcelRequest):
    """
    Opens the requested Excel file locally.
    """
    service = DesignerService()
    return service.open_excel(req.excel_path, req.sheet_name, req.password)

@router.post("/launch-ps")
async def launch_photoshop():
    """
    Triggers the Photoshop launch/connection.
    """
    service = DesignerService()
    return service.launch_photoshop()

@router.post("/calculate-layouts")
async def calculate_layouts():
    service = DesignerService()
    return service.enrich_active_sheet()

@router.post("/export-plans")
async def export_plans():
    service = DesignerService()
    return service.export_build_plans()

@router.post("/run-builder")
async def run_builder(req: RunBuilderRequest):
    """
    Triggers the Photoshop builder script with injected paths.
    """
    service = DesignerService()
    return service.run_photoshop_builder(images_dir=req.images_path)

@router.post("/sheets")
async def list_excel_sheets(req: SheetListRequest):
    agent = ExcelAgent()
    try:
        sheets = agent.list_sheets(req.excel_path, req.password)
        return sheets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        agent.quit()

@router.post("/sync-excel")
async def trigger_excel_sync(req: SyncTrigger):
    manager = SyncManager()
    try:
        result = manager.perform_sync(
            project_id=req.project_id,
            excel_path=req.excel_path,
            sheet_name=req.sheet_name,
            password=req.password
        )
        return {"status": "success", "hub_response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
