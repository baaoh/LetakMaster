import os
import json
import difflib
import xlwings as xw
from app.qa.psd_reader import PSDReader

class QAService:
    def __init__(self, excel_path=None, excel_password=None):
        self.excel_path = excel_path
        self.excel_password = excel_password
        
        # Paths
        self.root_dir = os.getcwd()
        self.qa_workspace = os.path.join(self.root_dir, "workspaces", "qa")
        self.scans_dir = os.path.join(self.qa_workspace, "scans")
        self.previews_dir = os.path.join(self.root_dir, "frontend_static", "previews")
        
        self.reader = PSDReader(self.scans_dir, self.previews_dir)

    def get_existing_scans(self):
        """
        Returns list of previously scanned files.
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
                        group_count = len(data.get("groups", {}))
                        
                        # Reconstruct preview path
                        preview_name = f"{page_name}.png"
                        preview_path = os.path.join(self.previews_dir, preview_name)
                        
                        results.append({
                            "page": page_name,
                            "json_path": full_path,
                            "preview_path": preview_path,
                            "group_count": group_count
                        })
                except:
                    pass
        
        # Sort by Page Number
        import re
        def sort_key(x):
            match = re.search(r'(\d+)', x['page'])
            return int(match.group(1)) if match else 0
            
        return sorted(results, key=sort_key)

    def run_import(self, psd_folder_or_files):
        """
        Processes a list of PSD files or a folder.
        Returns a summary report.
        """
        if isinstance(psd_folder_or_files, str):
            # It's a folder
            files = [os.path.join(psd_folder_or_files, f) for f in os.listdir(psd_folder_or_files) if f.lower().endswith(".psd")]
        else:
            files = psd_folder_or_files
            
        results = []
        for f in files:
            res = self.reader.process_file(f)
            if res:
                results.append(res)
                
        # Consolidate results into one big extraction dict for Excel writing
        # Structure: { "Product_01_XX": { "nazev_01a": "..." }, ... }
        consolidated = {}
        for r in results:
            with open(r['json_path'], 'r', encoding='utf-8') as jf:
                data = json.load(jf)
                # Flatten groups into global map
                # Warning: Duplicate Group IDs across pages (e.g. A4_Grp_01 on Page 10 and Page 11) will overwrite!
                # We MUST key by (Page, Group) or just assume Group IDs are unique PER PAGE and we iterate rows to find matches.
                # Actually, standard logic is Product_XX where XX is slot 1-16. This repeats every page.
                # SO: We need to know WHICH page the Excel row belongs to.
                
                page_name = data.get("page_name", "")
                # Try to extract page number from filename "Page 43" -> 43
                import re
                match = re.search(r'Page\s*_?\s*(\d+)', page_name, re.IGNORECASE)
                page_num = int(match.group(1)) if match else 0
                
                if page_num not in consolidated:
                    consolidated[page_num] = {}
                
                consolidated[page_num].update(data.get("groups", {}))
                
        # Write to Excel
        if self.excel_path:
            self._write_actuals_to_excel(consolidated)
            
        return results

    def _write_actuals_to_excel(self, consolidated_data):
        print(f"Writing actuals to Excel: {self.excel_path}")
        # Use visible=True to avoid issues if User has Excel open
        app = xw.App(visible=True) 
        try:
            # Check if book is already open in this app instance
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
            
            sheet = book.sheets.active # Assume active sheet for now
            
            # --- CONSTANTS ---
            COL_ACTUAL_START = 52
            
            headers = [
                "ACTUAL_Nazev_A", "ACTUAL_Nazev_B", "ACTUAL_Cena_A", "ACTUAL_Cena_B", 
                "ACTUAL_Od", "ACTUAL_EAN", "ACTUAL_Dostupnost"
            ]
            
            # Write Headers
            sheet.range((6, COL_ACTUAL_START + 1)).value = headers
            
            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
            data_range = sheet.range(f"V7:AM{last_row}").value # Read Page(V)..Alloc(AM)
            
            # We need to construct a write buffer
            # Size: (Rows, 7)
            write_buffer = [[None] * 7 for _ in range(len(data_range))]
            match_count = 0
            
            for i, row in enumerate(data_range):
                if not row: continue
                
                # Parse Page
                try: page_num = int(row[0]) 
                except: page_num = 0
                
                # Parse Group
                group_id = row[17] # AM
                if not group_id: continue

                # Normalize Group ID (Product_01_K -> Product_01)
                import re
                lookup_id = group_id
                # Match standard Product_XX or A4_Grp_XX
                # We strip _K, _EX, or other suffixes to find the base group from PSD scan
                # But we keep "A4_Grp_01" intact.
                # Regex: ^(Product_\d+|A4_Grp_\d+)
                m = re.match(r'^(Product_\d+|A4_Grp_\d+)', str(group_id), re.IGNORECASE)
                if m:
                    lookup_id = m.group(1)
                    # Normalize casing to what PSD Reader outputs (Product_01 with capital P? Reader uses Product_01 based on my fix)
                    # Actually Reader output depends on Regex construction.
                    # In reader: `norm_key = f"Product_{suffix}"` -> Title Case.
                    # Excel might use "Product_01" or "product_01".
                    # Let's ensure strict Title Case for lookup if that's what reader does.
                    parts = lookup_id.split('_')
                    if parts[0].lower() == "product":
                        lookup_id = f"Product_{parts[1]}"
                    elif parts[0].lower() == "a4":
                        # A4_Grp_XX
                        if len(parts) >= 3:
                            lookup_id = f"A4_Grp_{parts[2]}"
                
                if page_num in consolidated_data and lookup_id in consolidated_data[page_num]:
                    psd_group = consolidated_data[page_num][lookup_id]
                    layers = psd_group.get("layers", {})
                    match_count += 1
                    
                    # Extract Data using standard naming conventions
                    suffix = "00"
                    parts = str(lookup_id).split('_')
                    if len(parts) > 1: suffix = parts[-1] # 01
                    
                    # Helper to find layer text
                    def get_text(base_name):
                        # Try exact match first
                        key = f"{base_name}_{suffix}".lower()
                        if key in layers: return layers[key]["text"]
                        
                        # Try A/B variants for titles
                        key_a = f"{base_name}_{suffix}a".lower()
                        if key_a in layers: return layers[key_a]["text"]
                        
                        return None

                    # 1. Nazev A
                    write_buffer[i][0] = get_text("nazev") or get_text("nazev") 
                    
                    # 2. Nazev B
                    key_b = f"nazev_{suffix}b".lower()
                    if key_b in layers: write_buffer[i][1] = layers[key_b]["text"]
                    
                    # 3. Cena A
                    key_ca = f"cena_{suffix}a".lower()
                    if key_ca in layers: write_buffer[i][2] = layers[key_ca]["text"]
                    
                    # 4. Cena B
                    key_cb = f"cena_{suffix}b".lower()
                    if key_cb in layers: write_buffer[i][3] = layers[key_cb]["text"]
                    
                    # 5. Od
                    key_od = f"od_{suffix}".lower()
                    if key_od in layers and layers[key_od]["visible"]:
                        write_buffer[i][4] = layers[key_od]["text"]
                        
                    # 6. EAN (Number)
                    key_ean = f"ean-number_{suffix}".lower()
                    if key_ean not in layers: key_ean = f"ean_number_{suffix}".lower()
                    if key_ean not in layers: key_ean = f"ean_{suffix}".lower() # fallback
                    if key_ean in layers: write_buffer[i][5] = layers[key_ean]["text"]
                    
                    # 7. Dostupnost
                    key_dost = f"dostupnost_{suffix}".lower()
                    if key_dost in layers and layers[key_dost]["visible"]:
                        write_buffer[i][6] = layers[key_dost]["text"]

            print(f"Matched {match_count} rows from PSD data.")
            # Write extracted data
            sheet.range((7, COL_ACTUAL_START + 1)).value = write_buffer
            book.save()
            
        finally:
            # Do not quit if visible=True and it was already open?
            # If we created the app instance, we should probably quit it unless we want to leave it for user.
            # But the user asked for "Click Check -> Highlights".
            # If we quit, the user has to reopen.
            # Let's LEAVE IT OPEN if we used visible=True?
            # But subsequent calls might spawn new instances.
            # Let's try to quit ONLY if we didn't find an existing book? 
            # Simplified: Just don't quit if visible=True, let user close it.
            # But repeated runs will spawn multiple Excel processes if not careful.
            # xw.App(visible=True) usually connects to existing if strictly one? No, it creates new.
            # xw.apps.active might get existing.
            pass

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
            
            # ... (Rest of logic unchanged, just ensured visible=True) ...
            
            # Define Comparison Pairs (Exp_Col_Index, Act_Col_Index, Type)
            # 1-based indices relative to sheet
            pairs = [
                (39, 53, "fuzzy"), # Nazev A
                (40, 54, "fuzzy"), # Nazev B
                (45, 55, "exact"), # Cena A
                (46, 56, "exact"), # Cena B
                (41, 57, "exact"), # EAN
            ]
            
            orange_color = (255, 204, 153)
            mismatch_count = 0
            
            for r in range(7, last_row + 1):
                is_mismatch = False
                
                # Check if we have ANY actual data for this row?
                # If Actual is completely empty, it might be a missing scan.
                # Do we flag that? "Missing Scan" vs "Mismatch".
                # For now, treat as mismatch if Expected has data.
                
                has_actual = False
                for idx in range(53, 60):
                    if sheet.range((r, idx)).value:
                        has_actual = True
                        break
                
                for exp_idx, act_idx, mode in pairs:
                    val_exp = sheet.range((r, exp_idx)).value
                    val_act = sheet.range((r, act_idx)).value
                    
                    if not val_exp and not val_act: continue
                    
                    match = True
                    if mode == "exact":
                        s1 = str(val_exp).strip() if val_exp is not None else ""
                        s2 = str(val_act).strip() if val_act is not None else ""
                        # Float/Int normalization
                        try:
                            if float(s1) == float(s2): s1 = s2
                        except: pass
                        if s1 != s2: match = False
                    else:
                        s1 = str(val_exp).strip() if val_exp is not None else ""
                        s2 = str(val_act).strip() if val_act is not None else ""
                        if s1 == s2: match = True
                        else:
                            ratio = difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
                            if ratio < 0.8: match = False
                            
                    if not match:
                        is_mismatch = True
                        break
                
                # Apply Highlight
                target_range = sheet.range((r, 4), (r, 8))
                if is_mismatch:
                    target_range.color = orange_color
                    mismatch_count += 1
                    
                    # Link logic (unchanged)
                    page_val = sheet.range((r, 22)).value
                    grp_val = sheet.range((r, 39)).value
                    if page_val and grp_val:
                        link = f"http://127.0.0.1:5173/qa/inspect?page={int(page_val)}&group={grp_val}"
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
        finally:
            # app.quit() # Keep open for user to see
            pass
