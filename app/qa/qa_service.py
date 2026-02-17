import os
import json
import difflib
import re
import xlwings as xw
from app.qa.psd_reader import PSDReader
from app.qa.qa_matcher import QAMatcher
from app.database import ProjectState, AppConfig

class QAService:
    def __init__(self, db_session, state_id=None):
        self.db = db_session
        self.state_id = state_id
        
        # Resolve State
        if not self.state_id:
            # Default to latest state if not provided
            latest = self.db.query(ProjectState).order_by(ProjectState.created_at.desc()).first()
            if latest:
                self.state_id = latest.id
        
        self.state = self.db.query(ProjectState).get(self.state_id) if self.state_id else None
        
        # Paths
        self.root_dir = os.getcwd()
        
        if self.state:
            self.qa_workspace = os.path.join(self.root_dir, "workspaces", f"state_{self.state.id}", "qa")
            self.excel_path = self.state.last_workspace_path
        else:
            # Fallback (Should not happen in proper flow)
            self.qa_workspace = os.path.join(self.root_dir, "workspaces", "qa")
            self.excel_path = None
            
        self.scans_dir = os.path.join(self.qa_workspace, "scans")
        self.previews_dir = os.path.join(self.qa_workspace, "previews")
        
        # Ensure directories exist
        if not os.path.exists(self.scans_dir):
            os.makedirs(self.scans_dir)
        if not os.path.exists(self.previews_dir):
            os.makedirs(self.previews_dir)
            
        # Excel Password
        pass_conf = self.db.query(AppConfig).filter_by(key="excel_password").first()
        self.excel_password = pass_conf.value if pass_conf else None

        self.reader = PSDReader(self.scans_dir, self.previews_dir)
        self.matcher = QAMatcher()

    def get_existing_scans(self):
        """
        Returns list of previously scanned files for this state.
        """
        results = []
        if not os.path.exists(self.scans_dir):
            return []
            
        for f in os.listdir(self.scans_dir):
            if f.endswith(".json") and f.startswith("scan_"):
                full_path = os.path.join(self.scans_dir, f)
                try:
                    with open(full_path, "r", encoding="utf-8") as jf:
                        data = json.load(jf)
                        page_name = data.get("page_name", "")
                        layer_count = data.get("layer_count", len(data.get("layers", [])))
                        
                        # Preview Path (Relative for Frontend)
                        # Frontend maps /workspaces -> local workspaces folder
                        # We need to construct a URL that points to the file
                        # Assuming API serves static files from workspaces
                        preview_name = f"{page_name}.png"
                        # preview_url = f"/workspaces/state_{self.state_id}/qa/previews/{preview_name}"
                        # BUT: The frontend might need a different route.
                        # For now, let's just return the absolute path or filename.
                        
                        results.append({
                            "page": page_name,
                            "json_path": full_path,
                            "preview_name": preview_name,
                            "layer_count": layer_count
                        })
                except:
                    pass
        
        # Sort by Page Number
        def sort_key(x):
            match = re.search(r'(\d+)', x['page'])
            return int(match.group(1)) if match else 0
            
        return sorted(results, key=sort_key)

    def run_import(self, psd_folder_or_files):
        """
        Processes PSD files -> Raw Scan -> Matched against Build Plan -> Excel.
        """
        if isinstance(psd_folder_or_files, str):
            files = [os.path.join(psd_folder_or_files, f) for f in os.listdir(psd_folder_or_files) if f.lower().endswith(".psd")]
        else:
            files = psd_folder_or_files
            
        results = []
        processed_pages = []
        
        # 1. Process PSDs to get Raw Scans
        for f in files:
            res = self.reader.process_file(f)
            if res:
                results.append(res)
                processed_pages.append(res["page"])
        
        # 2. Locate Build Plans
        build_plans_dir = self._find_build_plans_dir()
        if not build_plans_dir:
            print("Warning: No Build Plans found for this state. Cannot match data.")
            return results

        print(f"Using Build Plans from: {build_plans_dir}")

        # 3. Match Scans to Plans
        consolidated_matches = {} # Page -> { GroupID -> { Attr -> Val } }
        
        for res in results:
            page_name = res["page"]
            match = re.search(r'(\d+)', page_name)
            page_num = int(match.group(1)) if match else 0
            
            scan_path = res["json_path"]
            plan_path = os.path.join(build_plans_dir, f"build_page_{page_num}.json")
            
            if os.path.exists(plan_path):
                print(f"Matching Page {page_num}...")
                matched_data = self.matcher.match_page(plan_path, scan_path)
                consolidated_matches[page_num] = matched_data
                
                # Save Match Result for Inspection UI
                match_json_path = os.path.join(self.scans_dir, f"matches_Page_{page_num}.json")
                try:
                    with open(match_json_path, "w", encoding="utf-8") as mf:
                        json.dump({
                            "page": page_num,
                            "matches": matched_data
                        }, mf, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Failed to save match JSON: {e}")

            else:
                print(f"No build plan found for Page {page_num} at {plan_path}")

        # 4. Write to Excel
        if self.excel_path and consolidated_matches:
            self._write_actuals_to_excel(consolidated_matches)
            
        return results

    def _find_build_plans_dir(self):
        """
        Locates the Build Plan directory for the current state.
        Prioritizes `last_build_plans_path` from DB.
        """
        if self.state and self.state.last_build_plans_path and os.path.exists(self.state.last_build_plans_path):
            return self.state.last_build_plans_path
            
        # Fallback: Look in workspaces/build_plans
        root_plans = os.path.join(self.root_dir, "workspaces", "build_plans")
        if not os.path.exists(root_plans):
            return None
            
        # Filter for state ID
        if self.state_id:
            suffix = f"_State_{self.state_id}"
            candidates = [os.path.join(root_plans, d) for d in os.listdir(root_plans) if suffix in d]
            if candidates:
                # Sort by time, newest first
                candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                return candidates[0]
        
        return None

    def _write_actuals_to_excel(self, consolidated_data):
        print(f"Writing actuals to Excel: {self.excel_path}")
        app = xw.App(visible=True) 
        try:
            book = None
            name = os.path.basename(self.excel_path)
            for b in app.books:
                if b.name == name:
                    book = b
                    break
            
            if not book:
                if self.excel_password:
                    book = app.books.open(self.excel_path, password=self.excel_password)
                else:
                    book = app.books.open(self.excel_path)
            
            sheet = book.sheets.active 
            
            # --- CONSTANTS ---
            COL_ACTUAL_START = 52 # Column AZ is 52. Wait. 
            # AZ is 26+26 = 52? No. Z=26, AA=27, AZ=52.
            # BA is 53.
            # Previous code said: COL_ACTUAL_START = 52
            # And wrote to COL_ACTUAL_START + 1 (53 = BA). Correct.
            
            headers = [
                "PSD_Nazev_A", "PSD_Nazev_B", "PSD_Cena_A", "PSD_Cena_B", 
                "PSD_Od", "PSD_EAN", "PSD_Dostupnost"
            ]
            
            # Write Headers at BA6
            sheet.range((6, 53)).value = headers
            
            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
            # Read Page(V)..Alloc(AM) -> V is 22. AM is 39.
            # Range V7:AM...
            # Column indices in range: Page is 0. Group is 17.
            data_range = sheet.range(f"V7:AM{last_row}").value 
            
            write_buffer = [[None] * 7 for _ in range(len(data_range))]
            match_count = 0
            
            for i, row in enumerate(data_range):
                if not row: continue
                
                try: page_num = int(row[0]) 
                except: page_num = 0
                
                group_id = row[17] # AM
                if not group_id: continue

                # Look up in consolidated data
                # consolidated_data[page_num][group_id]
                
                if page_num in consolidated_data and str(group_id) in consolidated_data[page_num]:
                    matched_group = consolidated_data[page_num][str(group_id)]
                    layers = matched_group.get("layers", {})
                    match_count += 1
                    
                    # Extract keys based on suffix logic in QAMatcher?
                    # No, QAMatcher uses the exact keys from Build Plan.
                    # Build Plan keys are constructed as: f"nazev_{suffix}A"
                    # We need to reconstruct the keys here to look them up.
                    
                    suffix = "00"
                    parts = str(group_id).split('_')
                    # A4_Grp_02 -> 02. Product_01 -> 01.
                    if len(parts) >= 2:
                        if parts[0].lower() == "product": suffix = parts[1]
                        elif parts[0].lower() == "a4" and len(parts) >= 3: suffix = parts[2]
                        
                    def get_val(base):
                        # base e.g. "nazev_01A"
                        # Keys in 'layers' are lowercased by QAMatcher? 
                        # Let's check QAMatcher: results[group_id]["layers"][key.lower()]
                        # Yes.
                        k = base.lower()
                        if k in layers:
                            item = layers[k]
                            if item["visible"]:
                                return item["text"]
                        return None

                    # 1. Nazev A
                    write_buffer[i][0] = get_val(f"nazev_{suffix}A")
                    # 2. Nazev B
                    write_buffer[i][1] = get_val(f"nazev_{suffix}B")
                    # 3. Cena A
                    write_buffer[i][2] = get_val(f"cena_{suffix}A")
                    # 4. Cena B
                    write_buffer[i][3] = get_val(f"cena_{suffix}B")
                    # 5. Od
                    write_buffer[i][4] = get_val(f"od_{suffix}")
                    # 6. EAN
                    # Try both variants
                    val_ean = get_val(f"EAN-number_{suffix}")
                    if not val_ean: val_ean = get_val(f"EAN_{suffix}")
                    write_buffer[i][5] = val_ean
                    # 7. Dostupnost
                    write_buffer[i][6] = get_val(f"dostupnost_{suffix}")

            print(f"Matched {match_count} rows from PSD data.")
            sheet.range((7, 53)).value = write_buffer
            book.save()
            
        except Exception as e:
            print(f"Excel Write Error: {e}")
            raise e

    def run_check(self):
        """
        Compares Expected vs Actual columns and Highlights Mismatches.
        """
        print(f"Running Check on: {self.excel_path}")
        app = xw.App(visible=True)
        try:
            book = None
            name = os.path.basename(self.excel_path)
            for b in app.books:
                if b.name == name:
                    book = b
                    break
            if not book:
                if self.excel_password:
                    book = app.books.open(self.excel_path, password=self.excel_password)
                else:
                    book = app.books.open(self.excel_path)
            
            sheet = book.sheets.active
            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
            
            # AM(39) -> Expected Nazev A.
            # BA(53) -> Actual Nazev A.
            
            # Pairs (Expected_Col_1Based, Actual_Col_1Based, Type)
            pairs = [
                (39, 53, "fuzzy"), # Nazev A
                (40, 54, "fuzzy"), # Nazev B
                (45, 55, "exact"), # Cena A
                (46, 56, "exact"), # Cena B
                (41, 57, "exact"), # EAN (Number)
                # (43, 59, "fuzzy"), # Dostupnost (Maybe? Not strictly critical usually)
            ]
            
            orange_color = (255, 204, 153)
            mismatch_count = 0
            
            # Read range for speed
            # Read Columns AM(39) to BG(59)?
            # Just iterating is fine for < 1000 rows usually. 
            # But let's check one row at a time or bulk read. 
            # Bulk read is safer.
            
            for r in range(7, last_row + 1):
                is_mismatch = False
                
                # Check if actual data exists
                has_actual = False
                for idx in range(53, 60):
                    if sheet.range((r, idx)).value:
                        has_actual = True
                        break
                
                # If no actual data, skip highlight (assume not scanned yet)
                if not has_actual: continue

                for exp_idx, act_idx, mode in pairs:
                    val_exp = sheet.range((r, exp_idx)).value
                    val_act = sheet.range((r, act_idx)).value
                    
                    # Normalize
                    s1 = str(val_exp).strip() if val_exp is not None else ""
                    s2 = str(val_act).strip() if val_act is not None else ""
                    
                    if not s1 and not s2: continue
                    if s1 and not s2: 
                        # Missing in Actual? Mismatch.
                        is_mismatch = True
                        break
                        
                    match = True
                    if mode == "exact":
                        try:
                            if float(s1) == float(s2): s1 = s2
                        except: pass
                        if s1 != s2: match = False
                    else:
                        if s1 == s2: match = True
                        else:
                            ratio = difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
                            if ratio < 0.8: match = False
                            
                    if not match:
                        is_mismatch = True
                        break
                
                # Highlight Range D:H (4:8)
                target_range = sheet.range((r, 4), (r, 8))
                if is_mismatch:
                    target_range.color = orange_color
                    mismatch_count += 1
                    
                    # Link
                    page_val = sheet.range((r, 22)).value
                    grp_val = sheet.range((r, 39)).value # AM
                    if page_val and grp_val:
                        link = f"http://localhost:5173/qa/inspect?page={int(page_val)}&group={grp_val}&state={self.state_id}"
                        try:
                            sheet.range((r, 4)).api.Hyperlinks.Add(
                                Anchor=sheet.range((r, 4)).api,
                                Address=link,
                                TextToDisplay=str(sheet.range((r, 4)).value or "Link")
                            )
                        except: pass
                else:
                    if target_range.color == orange_color:
                        target_range.color = None

            print(f"Check Complete. Found {mismatch_count} mismatches.")
            book.save()
        except Exception as e:
            print(f"Check Failed: {e}")
            raise e
