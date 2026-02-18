from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from client.agent.sync_manager import SyncManager
from client.automation.excel_agent import ExcelAgent

router = APIRouter(prefix="/automation", tags=["Automation"])

class SyncTrigger(BaseModel):
    project_id: int
    excel_path: str
    sheet_name: str
    password: Optional[str] = None

class SheetListRequest(BaseModel):
    excel_path: str
    password: Optional[str] = None

import subprocess

@router.post("/browse-file")
async def browse_excel_file():
    """
    Opens a native Windows file dialog via PowerShell.
    Works in portable environments without tkinter.
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

@router.post("/sheets")
async def list_excel_sheets(req: SheetListRequest):
    """
    Returns a list of sheet names for the UI dropdown.
    """
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
