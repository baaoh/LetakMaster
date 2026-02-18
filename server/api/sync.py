from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Optional
from core.models.schema import Project, ProjectState, PageSnapshot, DataDiff
from server.services.sync_coordinator import SyncCoordinator
from core.database import get_db

router = APIRouter(prefix="/sync", tags=["Sync"])

class SyncRequest(BaseModel):
    project_id: int
    user_id: str
    sheet_name: str
    excel_author: Optional[str] = "System"
    new_data: List[Dict] # List of Product Dicts
    archive_path: str # NAS Relative Path

@router.post("/push")
async def push_sync(req: SyncRequest, db: Session = Depends(get_db)):
    """
    Called by a Designer Client when they sync their local Excel.
    Creates a new shared State on the Synology Hub.
    """
    coordinator = SyncCoordinator(db)
    
    # 1. Verify Project Exists
    project = db.query(Project).get(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # 2. Orchestrate 'Git-Style' Sync
    try:
        result = coordinator.sync_project_data(
            project_id=req.project_id,
            user_id=req.user_id,
            sheet_name=req.sheet_name,
            excel_author=req.excel_author,
            new_data=req.new_data,
            archive_path=req.archive_path
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{project_id}")
async def get_state_history(project_id: int, db: Session = Depends(get_db)):
    """
    Returns the shared history for all users, now with Week (Sheet) context.
    """
    states = db.query(ProjectState).filter_by(project_id=project_id).order_by(ProjectState.created_at.desc()).all()
    
    return [
        {
            "id": s.id,
            "created_at": s.created_at,
            "created_by": s.created_by,
            "sheet_name": s.sheet_name,
            "excel_author": s.excel_author,
            "summary": s.summary,
            "parent_id": s.parent_state_id
        } for s in states
    ]

@router.get("/diff/{state_id}")
async def get_state_diff(state_id: int, db: Session = Depends(get_db)):
    """
    Returns the specific field changes for a given sync commit.
    """
    diffs = db.query(DataDiff).filter_by(state_id=state_id).all()
    
    return [
        {
            "page": d.page_number,
            "product": d.product_name,
            "field": d.field_name,
            "old": d.old_value,
            "new": d.new_value,
            "type": d.change_type
        } for d in diffs
    ]

@router.get("/snapshot/{state_id}")
async def get_full_snapshot(state_id: int, db: Session = Depends(get_db)):
    """
    Returns the full granular product data for a specific sync event.
    """
    state = db.query(ProjectState).filter(ProjectState.id == state_id).first()
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    return state.data_snapshot

@router.delete("/state/{state_id}")
async def delete_state(state_id: int, db: Session = Depends(get_db)):
    """
    Removes a sync state and its associated diffs and snapshots.
    """
    state = db.query(ProjectState).filter(ProjectState.id == state_id).first()
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    db.delete(state)
    db.commit()
    return {"status": "success", "message": f"Deleted state {state_id}"}
