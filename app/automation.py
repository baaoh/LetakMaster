import xlwings as xw
import sys
import os
import json
import re
from app.allocation_logic import SlotAllocator

class AutomationService:
    
    def enrich_active_workbook(self, sheet_name):
        """
        Only calculates layouts and writes them to columns AM-AY.
        """
        report = {"status": "pending", "details": ""}
        try:
            book = xw.books.active
            print(f"Enriching active workbook: {book.fullname}")
            self._enrich_logic(book, sheet_name)
            report["status"] = "success"
            report["details"] = "Layouts calculated and written to Excel."
            
            try:
                book.save()
            except:
                report["details"] += " (Manual Save Required)"
                
        except Exception as e:
            report["status"] = "error"
            report["details"] = str(e)
            print(f"Enrichment Error: {e}")
            raise e
            
        return report

    def generate_plans_from_active_workbook(self, sheet_name, state_id: int = None):
        """
        Reads columns AM-AY and generates JSON build plans.
        If state_id is provided, saves to internal managed path: workspaces/state_{id}/build_plans/
        Otherwise, falls back to timestamped folder.
        """
        report = {"status": "pending", "pages": [], "output_path": ""}
        try:
            try:
                book = xw.books.active
                # Verify connection by accessing a property
                _ = book.fullname
            except Exception as e:
                # OLE error 0x800a01a8 or others indicating disconnection
                print(f"Excel Connection Error: {e}")
                raise RuntimeError("Excel Workspace appears to be closed or unresponsive. Please Open Workspace and try again.")

            print(f"Generating JSON from: {book.fullname}")
            
            output_dir = ""
            import datetime
            timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M")
            safe_name = re.sub(r'[^\w\-_\. ]', '_', book.name)
            
            # Infer state_id from filename if missing
            if not state_id:
                # Matches "Workspace_State_1.xlsx" or similar patterns
                match = re.search(r"_State_(\d+)", book.name, re.IGNORECASE)
                if match:
                    state_id = int(match.group(1))
            
            # New Naming: YYMMDD_HHmm_ExcelName_State_{id}
            state_str = f"_State_{state_id}" if state_id else "_State_X"
            folder_name = f"{timestamp}_{safe_name}{state_str}"
            
            # Root for build plans
            root_plans_dir = os.path.join(os.getcwd(), "workspaces", "build_plans")
            
            # If state_id provided, we usually want it linked to the state.
            # But the user asked for a specific naming convention "folders... should be named..."
            # Let's put everything in workspaces/build_plans/YYMMDD... to be safe and consistent, 
            # OR put it inside the state folder with that name?
            # User said: "the folders where build plans are stored, should be named..."
            # This implies a global storage or a standardized format. 
            # To keep it clean and sortable by date as requested, a shared directory is better.
            
            output_dir = os.path.join(root_plans_dir, folder_name)
            
            # However, if we want to keep "State Isolation", we might put it in workspaces/state_X/build_plans/YYMMDD...
            # But the request "Run Builder Script should always take the newest Build Plans" implies a linear history is easier to track.
            # Let's use the shared `workspaces/build_plans` with the precise naming.
            
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            report["output_path"] = output_dir
            
            pages = self._generate_json_logic(book, sheet_name, output_dir_override=output_dir)
            report["status"] = "success"
            report["pages"] = pages
            
        except Exception as e:
            report["status"] = "error"
            report["error"] = str(e)
            print(f"Generation Error: {e}")
            raise e
            
        return report

    def run_attached_pipeline(self, sheet_name):
        """
        Legacy: Runs both steps.
        """
        enrich_rep = self.enrich_active_workbook(sheet_name)
        gen_rep = self.generate_plans_from_active_workbook(sheet_name)
        
        return {
            "enrichment": enrich_rep,
            "build_plans": gen_rep
        }

    def run_pipeline(self, file_path, sheet_name, password=None):
        """
        Runs the full automation pipeline on the given Excel file.
        mimicking the logic of scripts/enrich_excel.py and scripts/generate_build_json.py
        but in a single session.
        """
        report = {
            "enrichment": {"status": "skipped", "details": ""},
            "build_plans": {"status": "skipped", "pages": [], "count": 0}
        }
        
        # Mimic original script: App(visible=False)
        app = xw.App(visible=False)
        try:
            print(f"Opening {file_path} in background...")
            if password:
                book = app.books.open(file_path, password=password)
            else:
                book = app.books.open(file_path)
            
            # 1. Enrichment Logic
            try:
                self._enrich_logic(book, sheet_name)
                report["enrichment"]["status"] = "success"
                report["enrichment"]["details"] = "Layouts calculated and written to columns AM-AY."
            except Exception as e:
                report["enrichment"]["status"] = "error"
                report["enrichment"]["details"] = str(e)
                print(f"Enrichment Error: {e}")
                # If enrichment fails, we might still try generation if data exists? 
                # But likely pointless. Let's proceed anyway just in case.

            # 2. JSON Generation Logic
            try:
                # Use standard logic
                pages = self._generate_json_logic(book, sheet_name)
                report["build_plans"]["status"] = "success"
                report["build_plans"]["pages"] = pages
                report["build_plans"]["count"] = len(pages)
            except Exception as e:
                report["build_plans"]["status"] = "error"
                report["build_plans"]["error"] = str(e)
                print(f"JSON Gen Error: {e}")

            # Save once at the end
            book.save()
            print("Automation Complete. File saved.")
            
        except Exception as e:
            print(f"Pipeline Critical Error: {e}")
            raise e
        finally:
            # Always quit the dedicated background app
            app.quit()
            
        return report

    def _enrich_logic(self, book, sheet_name):
        # Source Columns (0-based)
        COL_EAN = 1      # B
        COL_PRODUCT = 3  # D: Název zboží
        COL_DESC = 4     # E: doplněk
        COL_GRAMAZ = 5   # F: gramáž
        COL_EANY_LBL = 6 # G: EANY (Input for Label)
        COL_ACS = 7      # H: Price Source
        COL_INT_KOD = 10 # K: Image Source
        COL_HERO = 11    # L: HERO
        COL_BRNO = 15    # P
        COL_USTI = 16    # Q
        COL_PAGE = 21    # V: page
        COL_PRICE = 22   # W: cena od
        COL_TDE = 24     # Y: TDE Availability

        HEADERS = [
            "PSD_Group", "PSD_Nazev_A", "PSD_Nazev_B", "PSD_EAN_Number", 
            "PSD_EAN_Label", "PSD_Dostupnost", "PSD_Od", "PSD_Cena_A", 
            "PSD_Cena_B", "PSD_Obraz", "PSD_Vis_Od", "PSD_Vis_EAN_Num", 
            "PSD_Vis_Dostupnost"
        ]

        EAN_LABEL_MAP = {
            "ean": "EAN:",
            "ean více druhů": "Více druhů",
            "ean 2 druhy": "2 druhy",
            "ean 3 druhy": "3 druhy",
            "ean 4 druhy": "4 druhy",
            "1": "EAN:",
            "2": "2 druhy",
            "3": "3 druhy",
            "4": "4 druhy",
            "všechny": "Všechny druhy",
            "více druhů": "Více druhů"
        }

        # Resolve Sheet
        if sheet_name not in [s.name for s in book.sheets]:
            # Fallback for workspace files that might have been renamed or are single-sheet
            sheet = book.sheets[0]
        else:
            sheet = book.sheets[sheet_name]

        # Determine Last Row
        try:
            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
        except:
            last_row = 100
            
        if last_row < 7:
            print("No data found for enrichment.")
            return

        print(f"Enriching rows 7 to {last_row}...")
        
        # Read source data (A to Y)
        data_range = sheet.range(f"A7:Y{last_row}").value
        # Read colors for Column H (Price Source) to detect highlights
        color_range = sheet.range(f"H7:H{last_row}")
        
        # Robust fetch: xlwings .color on large ranges can return a single value or 
        # a truncated list if formatting is sparse. We fetch via API for consistency.
        try:
            # Interior.Color returns a BGR long. We convert to RGB tuple or keep as is.
            # But simpler: just use xlwings cell-by-cell if needed, 
            # or use the .value equivalent for colors if possible.
            # Actually, the most reliable way to get a LIST is:
            h_colors = []
            raw_api_colors = color_range.api.Value # This won't work for colors.
            
            # Use a list comprehension over the range to get individual colors
            # This is slightly slower but 100% reliable for aligned indices.
            h_colors = [cell.color for cell in color_range]
        except Exception as e:
            print(f"Color Fetch Fallback active due to: {e}")
            h_colors = [None] * len(data_range)
        
        # Prepare Output Buffer
        output_data = [[None] * len(HEADERS) for _ in range(len(data_range))]
        pages = {} 
        
        # 1. Parse Data
        for r_offset, row in enumerate(data_range):
            if not row: continue
            if len(row) <= COL_TDE: continue # Row too short

            hero = row[COL_HERO]
            page = row[COL_PAGE]
            product = row[COL_PRODUCT]
            
            if page is not None and hero is not None:
                try:
                    h_val = int(float(hero))
                    p_val = int(float(page))
                    if p_val not in pages: pages[p_val] = []
                    pages[p_val].append({
                        'id': f"Idx_{r_offset}",
                        'hero': h_val,
                        'product': product
                    })
                except:
                    pass

        allocator = SlotAllocator()

        # 2. Allocation & Mapping
        for page_num in sorted(pages.keys()):
            products = pages[page_num]
            total_hero = sum(p['hero'] for p in products)
            
            # Page 1 Special Case: 8 Slots (4 rows x 2 cols)
            if page_num == 1:
                expected_hero = 8
                grid_cols = 2
            else:
                expected_hero = 16
                grid_cols = 4
            
            # A4 Detection
            if total_hero == 0:
                print(f"Page {page_num}: Detected as A4 (0 Hero). Skipping grid allocation.")
                continue

            if total_hero != expected_hero:
                print(f"Skipping Page {page_num}: Total Hero {total_hero} != {expected_hero}")
                continue

            try:
                # Re-instantiate allocator per page to handle different grid sizes
                allocator = SlotAllocator(rows=4, cols=grid_cols)
                
                results = allocator.allocate(products)
                for res in results:
                    idx = int(res['product_id'].split('_')[1])
                    src_row = data_range[idx]
                    
                    # --- Mapping Logic (Identical to original script) ---
                    # AM: Group
                    suffix = ""
                    if res['hero'] == 2:
                        suffix = "_K"
                    elif res['hero'] == 4:
                        suffix = "_EX"
                    
                    psd_group = f"Product_{res['start_slot']:02d}{suffix}"
                    output_data[idx][0] = psd_group
                    
                    # AN: Nazev A
                    output_data[idx][1] = str(src_row[COL_PRODUCT]) if src_row[COL_PRODUCT] else ""
                    
                    # AO: Nazev B
                    desc = str(src_row[COL_DESC]).strip() if src_row[COL_DESC] else ""
                    gram = str(src_row[COL_GRAMAZ]).strip() if src_row[COL_GRAMAZ] else ""
                    
                    if desc and gram:
                        output_data[idx][2] = f"{desc}\n{gram}"
                    else:
                        output_data[idx][2] = f"{desc}{gram}"
                    
                    # AP: EAN Number
                    ean_raw = src_row[COL_EAN]
                    ean_str = ""
                    if ean_raw is not None:
                        if isinstance(ean_raw, float):
                            ean_str = str(int(ean_raw))
                        else:
                            ean_str = str(ean_raw)
                    if len(ean_str) > 6:
                        output_data[idx][3] = "'" + ean_str[-6:]
                    else:
                        output_data[idx][3] = "'" + ean_str
                    
                    # AQ: EAN Label
                    raw_lbl = str(src_row[COL_EANY_LBL]).lower().strip() if src_row[COL_EANY_LBL] else ""
                    
                    # Robust Normalization
                    lbl_out = "EAN:" # Default
                    
                    # 1. Check for Numbers
                    try:
                        val_num = int(float(raw_lbl))
                        if val_num == 1:
                            lbl_out = "EAN:"
                        elif 1 < val_num <= 4:
                            lbl_out = f"{val_num} druhy" if val_num < 5 else f"{val_num} druhů"
                        else:
                            # 5 and up
                            lbl_out = "Více druhů"
                    except:
                        # 2. Check for Text Keywords
                        if "vše" in raw_lbl or "vse" in raw_lbl:
                            lbl_out = "Všechny druhy"
                        elif "víc" in raw_lbl or "vic" in raw_lbl:
                            lbl_out = "Více druhů"
                        elif "druh" in raw_lbl:
                            # Catch-all for "X druhu" if not caught above
                            lbl_out = raw_lbl.capitalize()

                    output_data[idx][4] = lbl_out
                    
                    # AR: Dostupnost
                    val_p = src_row[COL_BRNO]
                    val_q = src_row[COL_USTI]
                    val_y = src_row[COL_TDE]
                    
                    def is_zero(v):
                        try: return float(v) == 0
                        except: return False
                        
                    p0 = is_zero(val_p)
                    q0 = is_zero(val_q)
                    y0 = is_zero(val_y)
                    
                    msg = "•dostupné na všech pobočkách"
                    if p0 and q0 and y0: msg = "•pouze dostupné v Praze"
                    elif p0 and q0: msg = "•není dostupné v Brně, Ústí"
                    elif p0: msg = "•není dostupné v Brně"
                    elif q0: msg = "•není dostupné v Ústí"
                    elif y0: msg = "•není dostupné na TDE"
                    
                    output_data[idx][5] = msg
                    output_data[idx][6] = "od"
                    
                    # Prices
                    price_raw = src_row[COL_ACS]
                    p_int = ""
                    p_dec = ""
                    if price_raw is not None:
                        try:
                            f = float(str(price_raw).replace(',', '.'))
                            p_int = str(int(f))
                            dec_val = int(round((f - int(f)) * 100))
                            p_dec = f"{dec_val:02d}"
                        except:
                            p_int = str(price_raw)
                    output_data[idx][7] = p_int
                    output_data[idx][8] = p_dec
                    
                    output_data[idx][9] = str(src_row[COL_INT_KOD]) if src_row[COL_INT_KOD] else ""
                    
                    # Visibility
                    val_w = src_row[COL_PRICE]
                    
                    # Check for highlight in Column H (idx corresponds to row in data_range/h_colors)
                    row_color = h_colors[idx] if idx < len(h_colors) else None
                    is_highlighted = row_color is not None and row_color != (255, 255, 255) and row_color != 16777215
                    
                    vis_od = "TRUE"
                    
                    # Logic: 
                    # 1. Default: Visible if Column W (Price) has text.
                    # 2. Override: Visible if Highlighted AND EANY is NOT 1 (i.e., label is not "EAN:")
                    
                    has_price_text = val_w is not None and str(val_w).strip() != ""
                    is_plural = lbl_out != "EAN:"
                    
                    if is_highlighted and is_plural:
                        vis_od = "TRUE"
                    elif has_price_text:
                        vis_od = "TRUE"
                    else:
                        vis_od = "FALSE"
                    
                    output_data[idx][10] = vis_od
                    
                    vis_ean = "TRUE"
                    if lbl_out != "EAN:": vis_ean = "FALSE"
                    output_data[idx][11] = vis_ean
                    
                    vis_dost = "TRUE"
                    if msg == "•dostupné na všech pobočkách": vis_dost = "FALSE"
                    output_data[idx][12] = vis_dost
                        
            except Exception as e:
                print(f"Page {page_num} Allocation Error: {e}")

        # 3. Write Data
        sheet.range("AM6").value = HEADERS
        sheet.range("AM7").value = output_data

    def _generate_json_logic(self, book, sheet_name, output_dir_override=None):
        generated_pages = []
        
        # Resolve Sheet (Same logic)
        if sheet_name not in [s.name for s in book.sheets]:
            sheet = book.sheets[0]
        else:
            sheet = book.sheets[sheet_name]
        
        try:
            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
        except:
            last_row = 100
        
        # Read all (A to AY -> Index 50)
        # Note: We just wrote to AM-AY in memory, so reading back ensures we get the latest
        # (xlwings read/write syncs with the app instance).
        data = sheet.range(f"A7:AY{last_row}").value
        
        pages_data = {}
        COL_PAGE = 21
        
        for row in data:
            if not row: continue
            if len(row) <= COL_PAGE: continue
            
            try:
                p = int(float(row[COL_PAGE]))
                if p not in pages_data: pages_data[p] = []
                pages_data[p].append(row)
            except: pass
        
        for page_num, rows in pages_data.items():
            self._write_page_json(page_num, rows, book.fullname, output_dir_override)
            generated_pages.append(page_num)
            
        return generated_pages

    def _write_page_json(self, page_num, rows, base_path, output_dir_override=None):
        # Indices
        COL_ALLOC = 38
        COL_HERO = 11
        
        # Mappings
        COL_NAZEV_A = 39
        COL_NAZEV_B = 40
        COL_EAN_NUM = 41
        COL_EAN_LBL = 42
        COL_DOSTUPNOST = 43
        COL_OD = 44
        COL_CENA_A = 45
        COL_CENA_B = 46
        # ...
        COL_VIS_OD = 48
        COL_VIS_EAN = 49
        COL_VIS_DOST = 50
        
        build_plan = {
            "page": page_num,
            "actions": []
        }
        
        for row in rows:
            if len(row) <= 50: continue 
            
            psd_group = row[COL_ALLOC]
            if not psd_group: continue
            
            hero = row[COL_HERO]
            
            action = {
                "group": psd_group,
                "hero": hero,
                "data": {},
                "visibility": {}
            }
            
            suffix = psd_group.split('_')[1]
            
            def safe_str(val):
                if val is None: return ""
                if isinstance(val, float) and val.is_integer(): return str(int(val))
                return str(val)
            
            def is_true(val):
                return str(val).upper() == "TRUE"

            if row[COL_NAZEV_A]: action["data"][f"nazev_{suffix}A"] = safe_str(row[COL_NAZEV_A])
            if row[COL_NAZEV_B]: action["data"][f"nazev_{suffix}B"] = safe_str(row[COL_NAZEV_B])
            if row[COL_CENA_A]: action["data"][f"cena_{suffix}A"] = safe_str(row[COL_CENA_A])
            if row[COL_CENA_B]: action["data"][f"cena_{suffix}B"] = safe_str(row[COL_CENA_B])
            if row[COL_OD]: action["data"][f"od_{suffix}"] = safe_str(row[COL_OD])
            if row[COL_EAN_NUM]: action["data"][f"EAN-number_{suffix}"] = safe_str(row[COL_EAN_NUM])
            if row[COL_EAN_LBL]: action["data"][f"EAN:_{suffix}"] = safe_str(row[COL_EAN_LBL])
            if row[COL_DOSTUPNOST]: action["data"][f"dostupnost_{suffix}"] = safe_str(row[COL_DOSTUPNOST])
            
            # Map Image (AV / Index 47)
            COL_OBRAZ = 47
            if len(row) > COL_OBRAZ and row[COL_OBRAZ]: 
                action["data"][f"image_{suffix}"] = safe_str(row[COL_OBRAZ])
            
            if row[COL_VIS_OD] is not None: action["visibility"][f"od_{suffix}"] = is_true(row[COL_VIS_OD])
            if row[COL_VIS_EAN] is not None: action["visibility"][f"EAN-number_{suffix}"] = is_true(row[COL_VIS_EAN])
            if row[COL_VIS_DOST] is not None: action["visibility"][f"dostupnost_{suffix}"] = is_true(row[COL_VIS_DOST])
            
            build_plan["actions"].append(action)
        
        if output_dir_override:
            dir_path = output_dir_override
        else:
            dir_path = os.path.dirname(base_path)
            
        json_name = f"build_page_{page_num}.json"
        full_path = os.path.join(dir_path, json_name)
        
        json_name = f"build_page_{page_num}.json"
        full_path = os.path.join(dir_path, json_name)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(build_plan, f, indent=2, ensure_ascii=False)

def enrich_active_book():
    """
    Entry point for xlwings RunPython.
    Usage in VBA: RunPython ("import app.automation; app.automation.enrich_active_book()")
    """
    service = AutomationService()
    # Use active sheet name
    try:
        sheet_name = xw.books.active.sheets.active.name
        service.enrich_active_workbook(sheet_name)
    except Exception as e:
        # Show error in Excel
        try:
            xw.apps.active.api.StatusBar = f"Error: {e}"
        except:
            pass
        
        