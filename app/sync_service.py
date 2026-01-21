import json
from sqlalchemy.orm import Session
from app.database import AppConfig, ProjectState
from app.excel_service import ExcelService

class DiffService:
    def compare(self, state_a: list, state_b: list, key_field: str = None):
        """
        Compares two lists of dictionaries (rows).
        If key_field is provided, it matches rows by that key.
        Otherwise, it assumes order matters or hashes rows.
        For MVP, we'll assume state_a and state_b are flat lists of dicts.
        """
        report = {"added": [], "removed": [], "modified": []}
        
        # Helper to index data
        def index_data(data):
            indexed = {}
            for item in data:
                # If key_field exists and is in item, use it. Else use json dump as key (naive)
                if key_field and key_field in item:
                    key = item[key_field]
                else:
                    # Fallback: composite key of all first columns? or just json dump
                    # Ideally we have a primary key config. 
                    # For now, let's assuming row-matching isn't perfect without a PK.
                    # We will just iterate for this MVP implementation if no PK.
                    key = json.dumps(item, sort_keys=True)
                indexed[key] = item
            return indexed

        # If key_field is NOT provided, basic diffing is hard. 
        # But let's assume the caller provides one or we iterate.
        # In the test, we passed "Product".
        
        map_a = index_data(state_a)
        map_b = index_data(state_b)
        
        all_keys = set(map_a.keys()) | set(map_b.keys())
        
        for key in all_keys:
            val_a = map_a.get(key)
            val_b = map_b.get(key)
            
            if val_a is None:
                report["added"].append(val_b)
            elif val_b is None:
                report["removed"].append(val_a)
            elif val_a != val_b:
                # Compare fields
                changes = {}
                for k in set(val_a.keys()) | set(val_b.keys()):
                    if val_a.get(k) != val_b.get(k):
                        changes[k] = {"old": val_a.get(k), "new": val_b.get(k)}
                
                # Reconstruct "modified" entry
                mod_entry = val_b.copy() # Current state
                mod_entry["changes"] = changes
                report["modified"].append(mod_entry)
                
        return report

class SyncService:
    def __init__(self, db: Session):
        self.db = db
        self.excel = ExcelService()

    def sync_now(self, user_id: str):
        # 1. Get Config
        path_conf = self.db.query(AppConfig).filter_by(key="master_excel_path").first()
        sheet_conf = self.db.query(AppConfig).filter_by(key="watched_sheet_name").first()
        pass_conf = self.db.query(AppConfig).filter_by(key="excel_password").first()
        
        if not path_conf or not path_conf.value:
            raise ValueError("Master Excel Path not configured")
        
        file_path = path_conf.value
        sheet_name = sheet_conf.value if sheet_conf else None
        password = pass_conf.value if pass_conf else None
        
        print(f"DEBUG: SYNC - Starting sync for {file_path}, Sheet: {sheet_name}")
        
        # 2. Calculate Hash
        current_hash = self.excel.calculate_hash(file_path, sheet_name, password)
        print(f"DEBUG: SYNC - Hash calculated: {current_hash}")
        
        # 3. Check latest state (matching this source config?)
        # Ideally we check against the latest state *for this file/sheet*.
        # But for MVP we compare against absolute latest. 
        # If user switches files, it WILL generate a new state (hash diff), which is correct.
        latest_state = self.db.query(ProjectState).order_by(ProjectState.created_at.desc()).first()
        
        if latest_state and latest_state.excel_hash == current_hash and latest_state.source_path == file_path and latest_state.source_sheet == (sheet_name or "Sheet1"):
             return {"status": "no_change", "latest_id": latest_state.id}
        
        # 4. Parse and Save
        # Parse data. Assuming header is at row 6 as per previous logic, 
        print("DEBUG: SYNC - Hash different/new. Parsing file...")
        data = self.excel.parse_file(file_path, header_row=6, sheet_name=sheet_name, password=password)
        print(f"DEBUG: SYNC - Parsing complete. Rows: {len(data)}")
        
        # 5. Fetch Metadata
        metadata = self.excel.get_file_metadata(file_path, password)
        
        new_state = ProjectState(
            excel_hash=current_hash,
            data_snapshot_json=json.dumps(data),
            created_by=user_id,
            source_path=file_path,
            source_sheet=sheet_name or "Sheet1",
            excel_last_modified_by=metadata.get("last_modified_by")
        )
        self.db.add(new_state)
        self.db.commit()
        
        return {"status": "updated", "new_state_id": new_state.id}
