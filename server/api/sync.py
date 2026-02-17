from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Optional
from core.models.schema import Project, ProjectState, PageSnapshot, DataDiff
from server.services.sync_coordinator import SyncCoordinator
from app.database import get_db

router = APIRouter(prefix="/sync", tags=["Sync"])

class SyncRequest(BaseModel):
    project_id: int
    user_id: str
    new_data: List[Dict] # List of Product Dicts
    archive_path: str # NAS Relative Path (e.g. 'Archives/2026-08/state_5.xlsx')

@router.post("/push")
async def push_sync(req: SyncRequest, db: Session = Depends(get_db)):
    """
    Called by a Designer Client when they sync their local Excel.
    Creates a new shared Commit (ProjectState) on the Synology Hub.
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
            new_data=req.new_data,
            archive_path=req.archive_path
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{project_id}")
async def get_state_history(project_id: int, db: Session = Depends(get_db)):
    """
    Returns the shared history (Commits) for all users.
    """
    states = db.query(ProjectState).filter_by(project_id=project_id).order_by(ProjectState.created_at.desc()).all()
    
    return [
        {
            "id": s.id,
            "created_at": s.created_at,
            "created_by": s.created_by,
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
