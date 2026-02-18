from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Optional
from core.models.schema import Project, ProjectState, PageSnapshot, DataDiff
from core.utils.diff_service import DiffService
import json

class SyncCoordinator:
    """
    Orchestrates the 'Git-Style' sync on the Synology Hub.
    """
    def __init__(self, db: Session):
        self.db = db
        self.diff_engine = DiffService(key_field="product_name")

    def sync_project_data(self, project_id: int, user_id: str, sheet_name: str, excel_author: str, new_data: List[Dict], archive_path: str):
        """
        Processes a new sync event from a client.
        Restored with Sheet Context for granular timelines.
        """
        # 1. Get Parent State (FROM THE SAME SHEET/WEEK)
        parent_state = self.db.query(ProjectState)\
            .filter_by(project_id=project_id, sheet_name=sheet_name)\
            .order_by(ProjectState.created_at.desc())\
            .first()
        
        # 2. Group incoming data by Page
        pages_input = {}
        for row in new_data:
            p_num = row.get("page")
            if p_num:
                if p_num not in pages_input: pages_input[p_num] = []
                pages_input[p_num].append(row)

        # 3. Create the 'State'
        new_state = ProjectState(
            project_id=project_id,
            parent_state_id=parent_state.id if parent_state else None,
            created_by=user_id,
            sheet_name=sheet_name,
            excel_author=excel_author,
            archive_path=archive_path,
            data_snapshot=new_data
        )
        self.db.add(new_state)
        self.db.flush() 

        total_changes = []
        
        # 4. Per-Page Snapshotting
        for p_num, p_rows in pages_input.items():
            prev_snap = None
            if parent_state:
                prev_snap = self.db.query(PageSnapshot).filter_by(state_id=parent_state.id, page_number=p_num).first()
            
            # Calculate Changes
            is_dirty = True
            if prev_snap:
                page_diffs, summary = self.diff_engine.calculate_diff(prev_snap.data_json, p_rows)
                if not page_diffs:
                    is_dirty = False 
                else:
                    for d in page_diffs:
                        total_changes.append(DataDiff(
                            state_id=new_state.id,
                            page_number=p_num,
                            **d
                        ))
            
            new_snap = PageSnapshot(
                state_id=new_state.id,
                page_number=p_num,
                data_json=p_rows,
                is_dirty=is_dirty,
            )
            self.db.add(new_snap)

        # 5. Finalize
        new_state.summary = f"Week: {sheet_name}. {len(total_changes)} changes found."
        if total_changes:
            self.db.add_all(total_changes)
            
        self.db.commit()
        return {
            "state_id": new_state.id,
            "summary": new_state.summary,
            "changed_count": len(total_changes)
        }
