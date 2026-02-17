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

    def sync_project_data(self, project_id: int, user_id: str, new_data: List[Dict], archive_path: str):
        """
        Processes a new sync event from a client.
        1. Find latest state.
        2. Group new data by page.
        3. Diff per page.
        4. Save Commit (ProjectState) + PageSnapshots.
        """
        # 1. Get Parent State
        parent_state = self.db.query(ProjectState).filter_by(project_id=project_id).order_by(ProjectState.created_at.desc()).first()
        
        # 2. Group incoming data by Page
        pages_input = {}
        for row in new_data:
            p_num = row.get("page")
            if p_num:
                if p_num not in pages_input: pages_input[p_num] = []
                pages_input[p_num].append(row)

        # 3. Create the 'Commit'
        new_state = ProjectState(
            project_id=project_id,
            parent_state_id=parent_state.id if parent_state else None,
            created_by=user_id,
            archive_path=archive_path,
            data_snapshot=new_data # Full snapshot for easy reference
        )
        self.db.add(new_state)
        self.db.flush() # Get new_state.id

        total_changes = []
        
        # 4. Per-Page Snapshotting
        for p_num, p_rows in pages_input.items():
            # Find previous snapshot for this page
            prev_snap = None
            if parent_state:
                prev_snap = self.db.query(PageSnapshot).filter_by(state_id=parent_state.id, page_number=p_num).first()
            
            # Calculate Changes
            is_dirty = True
            if prev_snap:
                page_diffs, summary = self.diff_engine.calculate_diff(prev_snap.data_json, p_rows)
                if not page_diffs:
                    is_dirty = False # No content change, effectively a shallow copy
                else:
                    # Save granular diffs to the DB
                    for d in page_diffs:
                        total_changes.append(DataDiff(
                            state_id=new_state.id,
                            page_number=p_num,
                            **d
                        ))
            
            # Save the new snapshot
            new_snap = PageSnapshot(
                state_id=new_state.id,
                page_number=p_num,
                data_json=p_rows,
                is_dirty=is_dirty, # Signals designers that build plan is outdated
                # Build plan path stays None until a designer builds it
            )
            self.db.add(new_snap)

        # 5. Finalize
        new_state.summary = f"Processed {len(pages_input)} pages. {len(total_changes)} specific changes found."
        if total_changes:
            self.db.add_all(total_changes)
            
        self.db.commit()
        return {
            "state_id": new_state.id,
            "summary": new_state.summary,
            "changed_count": len(total_changes)
        }
