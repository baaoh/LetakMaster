import json
import shutil
import os
import time
from sqlalchemy.orm import Session
from app.database import AppConfig, ProjectState, ProductIndex
from app.excel_service import ExcelService
from app.utils import protect_file

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
        # Generator that yields status messages
        yield {"status": "progress", "message": "Reading Configuration..."}
        
        # 1. Get Config
        path_conf = self.db.query(AppConfig).filter_by(key="master_excel_path").first()
        sheet_conf = self.db.query(AppConfig).filter_by(key="watched_sheet_name").first()
        pass_conf = self.db.query(AppConfig).filter_by(key="excel_password").first()
        
        if not path_conf or not path_conf.value:
            yield {"status": "error", "message": "Master Excel Path not configured"}
            return
        
        file_path = path_conf.value
        sheet_name = sheet_conf.value if sheet_conf else None
        password = pass_conf.value if pass_conf else None
        
        yield {"status": "progress", "message": f"Calculating Hash for {sheet_name or 'Sheet 1'}..."}
        print(f"DEBUG: SYNC - Starting sync for {file_path}, Sheet: {sheet_name}")
        
        # 2. Calculate Hash
        try:
            current_hash = self.excel.calculate_hash(file_path, sheet_name, password)
        except Exception as e:
            yield {"status": "error", "message": f"Hash failed: {str(e)}"}
            return

        print(f"DEBUG: SYNC - Hash calculated: {current_hash}")
        
        # 3. Check latest state
        yield {"status": "progress", "message": "Checking against latest state..."}
        latest_state = self.db.query(ProjectState).order_by(ProjectState.created_at.desc()).first()
        
        if latest_state and latest_state.excel_hash == current_hash and latest_state.source_path == file_path and latest_state.source_sheet == (sheet_name or "Sheet1"):
             yield {"status": "done", "result": "no_change", "latest_id": latest_state.id}
             return
        
        # 4. Parse and Save
        yield {"status": "progress", "message": "Change detected. Parsing Excel file (this may take a moment)..."}
        print("DEBUG: SYNC - Hash different/new. Parsing file...")
        try:
            data = self.excel.parse_file(file_path, header_row=6, sheet_name=sheet_name, password=password)
        except Exception as e:
            yield {"status": "error", "message": f"Parsing failed: {str(e)}"}
            return

        print(f"DEBUG: SYNC - Parsing complete. Rows: {len(data)}")
        
        # 5. Archive Source File
        yield {"status": "progress", "message": "Archiving source sheet..."}
        ARCHIVE_DIR = "archive_files"
        if not os.path.exists(ARCHIVE_DIR):
            os.makedirs(ARCHIVE_DIR)
            
        # We always save archive as .xlsx because xlwings/Excel modern default is xlsx
        archive_name = f"state_{current_hash[:8]}_{int(time.time())}.xlsx"
        archive_full_path = os.path.abspath(os.path.join(ARCHIVE_DIR, archive_name))
        
        try:
            # Use high-fidelity sheet copy
            success = self.excel.archive_sheet(file_path, sheet_name, archive_full_path, password)
            if not success:
                print("Sheet archive failed, falling back to full copy?")
                # Fallback to full copy if specific copy fails?
                # shutil.copy2(file_path, archive_full_path) 
                # Note: Full copy would keep original extension.
                archive_full_path = None
            else:
                # Protect the archive immediately
                protect_file(archive_full_path)
        except Exception as e:
            print(f"Archive failed: {e}")
            archive_full_path = None

        # 6. Fetch Metadata
        yield {"status": "progress", "message": "Fetching metadata..."}
        metadata = self.excel.get_file_metadata(file_path, password)
        
        # 6a. Analyze Page Layouts
        page_stats = {} # { page_num: total_hero }
        for row in data:
            # Find Page/Hero Keys by heuristic scanning
            page_val = None
            hero_val = 0.0
            
            for k, v in row.items():
                if not v or "value" not in v: continue
                k_lower = k.lower()
                val = v["value"]
                if val is None: continue
                
                # Check for Page Column (usually 'page' or 'strana')
                if "page" in k_lower:
                    try: page_val = int(float(val))
                    except: pass
                
                # Check for Hero Column
                if "hero" in k_lower:
                    try: hero_val = float(val)
                    except: pass
            
            if page_val is not None:
                page_stats[page_val] = page_stats.get(page_val, 0) + hero_val
        
        page_metadata = {}
        for p, h_sum in page_stats.items():
            if h_sum == 0:
                layout = "A4"
            elif h_sum == 16:
                layout = "Grid16"
            elif p == 1 and h_sum == 8:
                layout = "Grid8"
            else:
                layout = f"Custom ({int(h_sum)} Hero)"
            page_metadata[str(p)] = layout

        yield {"status": "progress", "message": "Saving new state to database..."}
        new_state = ProjectState(
            excel_hash=current_hash,
            data_snapshot_json=json.dumps(data),
            page_metadata_json=json.dumps(page_metadata),
            created_by=user_id,
            source_path=file_path,
            source_sheet=sheet_name or "Sheet1",
            excel_last_modified_by=metadata.get("last_modified_by"),
            archive_path=archive_full_path
        )
        self.db.add(new_state)
        # Checkpoint here to get ID
        self.db.flush() 
        
        # 7. Index Products
        yield {"status": "progress", "message": "Indexing products..."}
        
        try:
            indices = []
            for row in data:
                # Heuristic mapping
                page = None
                product = None
                supplier = None
                ean = None
                psd = None
                
                for k, v in row.items():
                    if not v or "value" not in v: continue
                    val = v["value"]
                    if val is None: continue
                    val_str = str(val).strip()
                    if not val_str: continue
                    
                    k_lower = k.lower()
                    
                    if "page" in k_lower:
                        try: page = int(float(val))
                        except: pass
                    elif "zboží" in k_lower or "product" in k_lower:
                        product = val_str
                    elif "dodavatel" in k_lower or "supplier" in k_lower:
                        supplier = val_str
                    elif "ean" in k_lower:
                        if not ean: # Take first EAN found
                            ean = val_str
                    elif "psd_group" in k_lower:
                        psd = val_str
                
                if page and (product or supplier):
                    indices.append(ProductIndex(
                        project_state_id=new_state.id,
                        page_number=page,
                        product_name=product,
                        supplier_name=supplier,
                        ean=ean,
                        psd_group=psd
                    ))
            
            if indices:
                self.db.add_all(indices)
                print(f"DEBUG: Indexed {len(indices)} products.")
                
        except Exception as e:
            print(f"Indexing error: {e}")
            yield {"status": "error", "message": f"Indexing failed: {e}"}

        self.db.commit()
        
        yield {"status": "done", "result": "updated", "new_state_id": new_state.id}