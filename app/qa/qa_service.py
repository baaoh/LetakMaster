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
        app = xw.App(visible=False)
        try:
            if self.excel_password:
                book = app.books.open(self.excel_path, password=self.excel_password)
            else:
                book = app.books.open(self.excel_path)
            
            sheet = book.sheets.active # Assume active sheet for now
            
            # --- CONSTANTS ---
            COL_PAGE = 21 # V (0-based: 21)
            COL_ALLOC = 38 # AM
            
            # Target Columns (BA -> 52)
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
            
            for i, row in enumerate(data_range):
                if not row: continue
                
                # Parse Page
                try: page_num = int(row[0]) # Column V is index 0 in this slice
                except: page_num = 0
                
                # Parse Group
                # Column AM is index 17 in slice (V..AM is 22..38 => 17 columns)
                # Wait: V=21, AM=38. 38-21 = 17. Index 17 is correct.
                group_id = row[17] 
                
                if page_num in consolidated_data and group_id in consolidated_data[page_num]:
                    psd_group = consolidated_data[page_num][group_id]
                    layers = psd_group.get("layers", {})
                    
                    # Extract Data using standard naming conventions
                    # We need to guess the suffix based on group ID
                    # e.g. Product_01 -> suffix 01
                    suffix = "00"
                    parts = str(group_id).split('_')
                    if len(parts) > 1: suffix = parts[-1] # 01, 02, etc
                    
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
                    write_buffer[i][0] = get_text("nazev") or get_text("nazev") # Logic inside handles suffixes
                    
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
                    # Try "ean-number", "ean_number", "ean"
                    key_ean = f"ean-number_{suffix}".lower()
                    if key_ean not in layers: key_ean = f"ean_number_{suffix}".lower()
                    if key_ean in layers: write_buffer[i][5] = layers[key_ean]["text"]
                    
                    # 7. Dostupnost
                    key_dost = f"dostupnost_{suffix}".lower()
                    if key_dost in layers and layers[key_dost]["visible"]:
                        write_buffer[i][6] = layers[key_dost]["text"]

            # Write extracted data
            sheet.range((7, COL_ACTUAL_START + 1)).value = write_buffer
            book.save()
            
        finally:
            app.quit()

    def run_check(self):
        """
        Compares Expected vs Actual columns and Highlights Mismatches.
        """
        app = xw.App(visible=False)
        try:
            if self.excel_password:
                book = app.books.open(self.excel_path, password=self.excel_password)
            else:
                book = app.books.open(self.excel_path)
            
            sheet = book.sheets.active
            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
            
            # Read Expected (AM-AY) -> Cols 38-50 (Indices)
            # Read Actual (BA-BG) -> Cols 52-58
            
            # Let's read strictly the columns we compare
            # Nazev A: AM (39) vs BA (53)
            # Nazev B: AN (40) vs BB (54)
            # Cena A:  AS (45) vs BC (55)
            # Cena B:  AT (46) vs BD (56)
            # EAN:     AO (41) vs BF (57)
            
            # 1-based indices for xlwings range
            # AM=39, BA=53
            
            # Define Comparison Pairs (Exp_Col_Index, Act_Col_Index, Type)
            # 1-based indices relative to sheet
            pairs = [
                (39, 53, "fuzzy"), # Nazev A
                (40, 54, "fuzzy"), # Nazev B
                (45, 55, "exact"), # Cena A
                (46, 56, "exact"), # Cena B
                (41, 57, "exact"), # EAN
            ]
            
            # Columns D-H to highlight (4, 5, 6, 7, 8)
            highlight_cols = [4, 5, 6, 7, 8]
            
            orange_color = (255, 204, 153) # Light Orange roughly
            
            # Iterate rows
            for r in range(7, last_row + 1):
                is_mismatch = False
                
                for exp_idx, act_idx, mode in pairs:
                    val_exp = sheet.range((r, exp_idx)).value
                    val_act = sheet.range((r, act_idx)).value
                    
                    if not val_exp and not val_act: continue
                    
                    match = True
                    if mode == "exact":
                        # Strip whitespace and compare
                        s1 = str(val_exp).strip() if val_exp is not None else ""
                        s2 = str(val_act).strip() if val_act is not None else ""
                        if s1 != s2: match = False
                    else:
                        # Fuzzy
                        s1 = str(val_exp).strip() if val_exp is not None else ""
                        s2 = str(val_act).strip() if val_act is not None else ""
                        
                        if s1 == s2: 
                            match = True
                        else:
                            # Token sort ratio or simple ratio
                            ratio = difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
                            if ratio < 0.8: match = False
                            
                    if not match:
                        is_mismatch = True
                        break
                
                # Apply Highlight
                target_range = sheet.range((r, 4), (r, 8))
                if is_mismatch:
                    target_range.color = orange_color
                    
                    # Add Link to Product Name (Col 4 / D)
                    # We need page and group to build link
                    page_num = sheet.range((r, 21)).value # Col V (21 is index? No 21 is U. V is 22)
                    # Wait, 1-based: V is 22.
                    # Previous code said COL_PAGE=21 (0-based).
                    # xlwings range((r, c)) uses 1-based.
                    page_val = sheet.range((r, 22)).value
                    grp_val = sheet.range((r, 39)).value # AM
                    
                    if page_val and grp_val:
                        link = f"http://127.0.0.1:5173/qa/inspect?page={int(page_val)}&group={grp_val}"
                        # xlwings doesn't support easy hyperlink adding via standard API on range object in some versions?
                        # Use api formula
                        # formula = =HYPERLINK("url", "text")
                        # But we want to keep text.
                        # sheet.range((r, 4)).add_hyperlink(link, text_to_display=...) works in newer xlwings
                        try:
                            sheet.range((r, 4)).api.Hyperlinks.Add(
                                Anchor=sheet.range((r, 4)).api,
                                Address=link,
                                TextToDisplay=str(sheet.range((r, 4)).value or "Link")
                            )
                        except:
                            pass
                else:
                    # Clear color if fixed
                    # Check if it was orange? Or just clear always?
                    # Clearing might remove other formatting. Ideally only clear if it matches our orange.
                    if target_range.color == orange_color:
                        target_range.color = None

            book.save()
        finally:
            app.quit()
