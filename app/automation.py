import xlwings as xw
import sys
import os
import json
import re
from app.allocation_logic import SlotAllocator
from app.clustering import ProductClusterer

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
        """
        report = {"status": "pending", "pages": [], "output_path": ""}
        try:
            try:
                book = xw.books.active
                # Verify connection by accessing a property
                _ = book.fullname
            except Exception as e:
                print(f"Excel Connection Error: {e}")
                raise RuntimeError("Excel Workspace appears to be closed or unresponsive. Please Open Workspace and try again.")

            print(f"Generating JSON from: {book.fullname}")
            
            import datetime
            timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M")
            safe_name = re.sub(r'[^\w\-_\. ]', '_', book.name)
            
            if not state_id:
                match = re.search(r"_State_(\d+)", book.name, re.IGNORECASE)
                if match:
                    state_id = int(match.group(1))
            
            state_str = f"_State_{state_id}" if state_id else "_State_X"
            folder_name = f"{timestamp}_{safe_name}{state_str}"
            
            root_plans_dir = os.path.join(os.getcwd(), "workspaces", "build_plans")
            output_dir = os.path.join(root_plans_dir, folder_name)
            
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
        enrich_rep = self.enrich_active_workbook(sheet_name)
        gen_rep = self.generate_plans_from_active_workbook(sheet_name)
        return {
            "enrichment": enrich_rep,
            "build_plans": gen_rep
        }

    def run_pipeline(self, file_path, sheet_name, password=None):
        report = {
            "enrichment": {"status": "skipped", "details": ""},
            "build_plans": {"status": "skipped", "pages": [], "count": 0}
        }
        
        app = xw.App(visible=False)
        try:
            print(f"Opening {file_path} in background...")
            if password:
                book = app.books.open(file_path, password=password)
            else:
                book = app.books.open(file_path)
            
            try:
                self._enrich_logic(book, sheet_name)
                report["enrichment"]["status"] = "success"
                report["enrichment"]["details"] = "Layouts calculated and written to columns AM-AY."
            except Exception as e:
                report["enrichment"]["status"] = "error"
                report["enrichment"]["details"] = str(e)
                print(f"Enrichment Error: {e}")

            try:
                pages = self._generate_json_logic(book, sheet_name)
                report["build_plans"]["status"] = "success"
                report["build_plans"]["pages"] = pages
                report["build_plans"]["count"] = len(pages)
            except Exception as e:
                report["build_plans"]["status"] = "error"
                report["build_plans"]["error"] = str(e)
                print(f"JSON Gen Error: {e}")

            book.save()
            print("Automation Complete. File saved.")
            
        except Exception as e:
            print(f"Pipeline Critical Error: {e}")
            raise e
        finally:
            app.quit()
            
        return report

    def _enrich_logic(self, book, sheet_name):
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

        if sheet_name not in [s.name for s in book.sheets]:
            sheet = book.sheets[0]
        else:
            sheet = book.sheets[sheet_name]

        try:
            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
        except:
            last_row = 100
            
        if last_row < 7:
            print("No data found for enrichment.")
            return

        print(f"Enriching rows 7 to {last_row}...")
        
        data_range = sheet.range(f"A7:Y{last_row}").value
        color_range = sheet.range(f"H7:H{last_row}")
        
        try:
            h_colors = [cell.color for cell in color_range]
        except Exception as e:
            print(f"Color Fetch Fallback active due to: {e}")
            h_colors = [None] * len(data_range)
        
        output_data = [[None] * len(HEADERS) for _ in range(len(data_range))]
        pages = {} 
        
        # 1. Parse Data
        for r_offset, row in enumerate(data_range):
            if not row: continue
            if len(row) <= COL_TDE: continue 

            hero = row[COL_HERO]
            page = row[COL_PAGE]
            product = row[COL_PRODUCT]
            
            p_val = None
            if page is not None:
                try: p_val = int(float(page))
                except: pass
            
            if p_val is not None:
                if p_val not in pages: pages[p_val] = []
                
                h_val = 0
                if hero is not None:
                    try: 
                        val = int(float(hero))
                        if val in [1, 2, 4]:
                            h_val = val
                        else:
                            h_val = 0 # Invalid becomes 0
                    except: pass
                
                # Extract Price and Weight for Clustering
                raw_price = row[COL_PRICE]
                raw_weight = row[COL_GRAMAZ]
                
                price_val = 0.0
                if raw_price:
                    try:
                        price_val = float(str(raw_price).replace(',', '.'))
                    except: pass

                pages[p_val].append({
                    'id': f"Idx_{r_offset}",
                    'offset': r_offset,
                    'hero': h_val,
                    'product': product,
                    'name': str(product) if product else "",
                    'price': price_val,
                    'weight_text': str(raw_weight) if raw_weight else ""
                })

        allocator = SlotAllocator()
        clusterer = ProductClusterer()

        # 2. Allocation & Mapping
        for page_num in sorted(pages.keys()):
            products = pages[page_num]
            total_hero = sum(p['hero'] for p in products)
            
            if page_num == 1:
                expected_hero = 8
                grid_cols = 2
            else:
                expected_hero = 16
                grid_cols = 4

            # Decision: Grid or A4?
            is_grid = (total_hero == expected_hero)
            
            if is_grid:
                # --- STANDARD GRID LOGIC ---
                try:
                    # Filter out garbage rows (Hero 0) to prevent them from consuming slots
                    valid_products = [p for p in products if p['hero'] > 0]
                    
                    allocator = SlotAllocator(rows=4, cols=grid_cols)
                    results = allocator.allocate(valid_products)
                    for res in results:
                        idx = int(res['product_id'].split('_')[1])
                        src_row = data_range[idx]
                        
                        suffix = ""
                        if res['hero'] == 2: suffix = "_K"
                        elif res['hero'] == 4: suffix = "_EX"
                        
                        psd_group = f"Product_{res['start_slot']:02d}{suffix}"
                        output_data[idx][0] = psd_group
                        
                        output_data[idx][1] = str(src_row[COL_PRODUCT]) if src_row[COL_PRODUCT] else ""
                        
                        desc = str(src_row[COL_DESC]).strip() if src_row[COL_DESC] else ""
                        gram = str(src_row[COL_GRAMAZ]).strip() if src_row[COL_GRAMAZ] else ""
                        if desc and gram: output_data[idx][2] = f"{desc}\n{gram}"
                        else: output_data[idx][2] = f"{desc}{gram}"
                        
                        ean_raw = src_row[COL_EAN]
                        ean_str = ""
                        if ean_raw is not None:
                            if isinstance(ean_raw, float): ean_str = str(int(ean_raw))
                            else: ean_str = str(ean_raw)
                        output_data[idx][3] = "'" + ean_str[-6:] if len(ean_str) > 6 else "'" + ean_str
                        
                        raw_lbl = str(src_row[COL_EANY_LBL]).lower().strip() if src_row[COL_EANY_LBL] else ""
                        lbl_out = "EAN:"
                        try:
                            val_num = int(float(raw_lbl))
                            if val_num == 1: lbl_out = "EAN:"
                            elif 1 < val_num <= 4: lbl_out = f"{val_num} druhy" if val_num < 5 else f"{val_num} druhů"
                            else: lbl_out = "Více druhů"
                        except:
                            if "vše" in raw_lbl or "vse" in raw_lbl: lbl_out = "Všechny druhy"
                            elif "víc" in raw_lbl or "vic" in raw_lbl: lbl_out = "Více druhů"
                            elif "druh" in raw_lbl: lbl_out = raw_lbl.capitalize()
                        output_data[idx][4] = lbl_out
                        
                        val_p = src_row[COL_BRNO]
                        val_q = src_row[COL_USTI]
                        val_y = src_row[COL_TDE]
                        def is_zero(v):
                            try: return float(v) == 0
                            except: return False
                        p0 = is_zero(val_p); q0 = is_zero(val_q); y0 = is_zero(val_y)
                        msg = "•dostupné na všech pobočkách"
                        if p0 and q0 and y0: msg = "•pouze dostupné v Praze"
                        elif p0 and q0: msg = "•není dostupné v Brně, Ústí"
                        elif p0: msg = "•není dostupné v Brně"
                        elif q0: msg = "•není dostupné v Ústí"
                        elif y0: msg = "•není dostupné na TDE"
                        output_data[idx][5] = msg
                        output_data[idx][6] = "od"
                        
                        price_raw = src_row[COL_ACS]
                        p_int = ""; p_dec = ""
                        if price_raw is not None:
                            try:
                                f = float(str(price_raw).replace(',', '.'))
                                p_int = str(int(f))
                                dec_val = int(round((f - int(f)) * 100))
                                p_dec = f"{dec_val:02d}"
                            except: p_int = str(price_raw)
                        output_data[idx][7] = p_int
                        output_data[idx][8] = p_dec
                        
                        output_data[idx][9] = str(src_row[COL_INT_KOD]) if src_row[COL_INT_KOD] else ""
                        
                        val_w = src_row[COL_PRICE]
                        row_color = h_colors[idx] if idx < len(h_colors) else None
                        is_highlighted = row_color is not None and row_color != (255, 255, 255) and row_color != 16777215
                        
                        has_price_text = val_w is not None and str(val_w).strip() != ""
                        is_plural = lbl_out != "EAN:"
                        vis_od = "TRUE" if (is_highlighted and is_plural) or has_price_text else "FALSE"
                        output_data[idx][10] = vis_od
                        
                        vis_ean = "TRUE"
                        if lbl_out != "EAN:": vis_ean = "FALSE"
                        output_data[idx][11] = vis_ean
                        
                        vis_dost = "TRUE"
                        if msg == "•dostupné na všech pobočkách": vis_dost = "FALSE"
                        output_data[idx][12] = vis_dost
                            
                except Exception as e:
                    print(f"Page {page_num} Allocation Error: {e}")

            else:
                # --- A4 / UNSTRUCTURED LOGIC (Fallback) ---
                print(f"Page {page_num}: Total Hero {total_hero} != {expected_hero}. Running Clustering Logic...")
                
                # Filter out items with empty names to avoid creating groups for empty rows
                valid_a4_products = [p for p in products if p['name'] and p['name'].strip()]
                
                groups = clusterer.group_items(valid_a4_products)
                print(f"  -> Created {len(groups)} groups for Page {page_num}.")
                
                for grp_idx, grp in enumerate(groups, 1):
                    group_id_str = f"A4_Grp_{grp_idx:02d}"
                    leader_item = grp[0]
                    
                    grp_names = [x['name'] for x in grp]
                    nazev_a = clusterer.generate_smart_title(grp_names)
                    nazev_b = clusterer.generate_variants(grp, nazev_a)
                    
                    count = len(grp)
                    label = "EAN:" if count == 1 else (f"{count} druhy" if count <= 4 else "více druhů")
                    
                    for item in grp:
                        idx = item['offset']
                        src_row = data_range[idx]
                        
                        output_data[idx][0] = group_id_str
                        
                        if item == leader_item:
                            output_data[idx][1] = nazev_a
                            output_data[idx][2] = nazev_b
                            output_data[idx][4] = label
                        else:
                            output_data[idx][1] = str(src_row[COL_PRODUCT]) if src_row[COL_PRODUCT] else ""
                            output_data[idx][2] = str(src_row[COL_DESC]) if src_row[COL_DESC] else ""
                        
                        ean_raw = src_row[COL_EAN]
                        ean_str = ""
                        if ean_raw is not None:
                            if isinstance(ean_raw, float): ean_str = str(int(ean_raw))
                            else: ean_str = str(ean_raw)
                        output_data[idx][3] = "'" + ean_str[-6:] if len(ean_str) > 6 else "'" + ean_str
                        
                        val_p = src_row[COL_BRNO]
                        val_q = src_row[COL_USTI]
                        val_y = src_row[COL_TDE]
                        
                        def is_zero(v):
                            try: return float(v) == 0
                            except: return False
                            
                        p0 = is_zero(val_p); q0 = is_zero(val_q); y0 = is_zero(val_y)
                        msg = "•dostupné na všech pobočkách"
                        if p0 and q0 and y0: msg = "•pouze dostupné v Praze"
                        elif p0 and q0: msg = "•není dostupné v Brně, Ústí"
                        elif p0: msg = "•není dostupné v Brně"
                        elif q0: msg = "•není dostupné v Ústí"
                        elif y0: msg = "•není dostupné na TDE"
                        
                        output_data[idx][5] = msg
                        output_data[idx][6] = "od"
                        
                        price_raw = src_row[COL_ACS]
                        p_int = ""; p_dec = ""
                        if price_raw is not None:
                            try:
                                f = float(str(price_raw).replace(',', '.'))
                                p_int = str(int(f))
                                dec_val = int(round((f - int(f)) * 100))
                                p_dec = f"{dec_val:02d}"
                            except: p_int = str(price_raw)
                        output_data[idx][7] = p_int
                        output_data[idx][8] = p_dec
                        
                        output_data[idx][9] = str(src_row[COL_INT_KOD]) if src_row[COL_INT_KOD] else ""
                        
                        val_w = src_row[COL_PRICE]
                        has_price_text = val_w is not None and str(val_w).strip() != ""
                        row_color = h_colors[idx] if idx < len(h_colors) else None
                        is_highlighted = row_color is not None and row_color != (255, 255, 255) and row_color != 16777215
                        
                        vis_od = "TRUE" if (is_highlighted or has_price_text) else "FALSE"
                        output_data[idx][10] = vis_od
                        
                        vis_ean = "TRUE"
                        if output_data[idx][4] != "EAN:": vis_ean = "FALSE"
                        output_data[idx][11] = vis_ean
                        
                        vis_dost = "FALSE" if msg == "•dostupné na všech pobočkách" else "TRUE"
                        output_data[idx][12] = vis_dost

        sheet.range("AM6").value = HEADERS
        sheet.range("AM7").value = output_data

    def _generate_json_logic(self, book, sheet_name, output_dir_override=None):
        generated_pages = []
        
        if sheet_name not in [s.name for s in book.sheets]:
            sheet = book.sheets[0]
        else:
            sheet = book.sheets[sheet_name]
        
        try:
            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
        except:
            last_row = 100
        
        data = sheet.range(f"A7:AY{last_row}").value
        
        pages_data = {} # Dictionary to store rows grouped by page number
        COL_PAGE = 21
        
        for row in data:
            if not row: continue
            if len(row) <= COL_PAGE: continue
            
            try:
                p = int(float(row[COL_PAGE]))
                if p not in pages_data: pages_data[p] = []
                pages_data[p].append(row)
            except:
                # Ignore rows where page number is not a valid integer
                pass
        
        for page_num, rows in pages_data.items():
            self._write_page_json(page_num, rows, book.fullname, output_dir_override)
            generated_pages.append(page_num)
            
        return generated_pages

    def _write_page_json(self, page_num, rows, base_path, output_dir_override=None):
        COL_ALLOC = 38
        COL_HERO = 11
        
        COL_NAZEV_A = 39
        COL_NAZEV_B = 40
        COL_EAN_NUM = 41
        COL_EAN_LBL = 42
        COL_DOSTUPNOST = 43
        COL_OD = 44
        COL_CENA_A = 45
        COL_CENA_B = 46
        COL_OBRAZ = 47
        COL_VIS_OD = 48
        COL_VIS_EAN = 49
        COL_VIS_DOST = 50
        
        build_plan = {
            "page": page_num,
            "actions": []
        }
        
        for row in rows:
            # Ensure row has enough columns to avoid index errors
            if len(row) <= COL_VIS_DOST: continue 
            
            psd_group = row[COL_ALLOC]
            if not psd_group: continue # Skip if no allocation group is defined
            
            hero = row[COL_HERO]
            
            action = {
                "group": psd_group,
                "hero": hero,
                "data": {},
                "visibility": {}
            }
            
            try:
                # Extract suffix from group name (e.g., 'K' or 'EX')
                suffix = psd_group.split('_')[1]
            except IndexError:
                suffix = "00" # Default suffix if not found
            
            def safe_str(val):
                """Safely convert value to string, handling None and floats."""
                if val is None: return ""
                # Convert floats that are integers to int string (e.g., 5.0 -> "5")
                if isinstance(val, float) and val.is_integer(): return str(int(val))
                return str(val)
            
            def is_true(val):
                """Check if a value represents TRUE (case-insensitive)."""
                return str(val).upper() == "TRUE"

            # Populate action data based on available columns and suffix
            if row[COL_NAZEV_A]: action["data"][f"nazev_{suffix}A"] = safe_str(row[COL_NAZEV_A])
            if row[COL_NAZEV_B]: action["data"][f"nazev_{suffix}B"] = safe_str(row[COL_NAZEV_B])
            if row[COL_CENA_A]: action["data"][f"cena_{suffix}A"] = safe_str(row[COL_CENA_A])
            if row[COL_CENA_B]: action["data"][f"cena_{suffix}B"] = safe_str(row[COL_CENA_B])
            if row[COL_OD]: action["data"][f"od_{suffix}"] = safe_str(row[COL_OD])
            if row[COL_EAN_NUM]: action["data"][f"EAN-number_{suffix}"] = safe_str(row[COL_EAN_NUM])
            if row[COL_EAN_LBL]: action["data"][f"EAN:_{suffix}"] = safe_str(row[COL_EAN_LBL])
            if row[COL_DOSTUPNOST]: action["data"][f"dostupnost_{suffix}"] = safe_str(row[COL_DOSTUPNOST])
            
            # Check if image column exists and has value
            if len(row) > COL_OBRAZ and row[COL_OBRAZ]: 
                action["data"][f"image_{suffix}"] = safe_str(row[COL_OBRAZ])
            
            # Populate visibility settings if values are present
            if row[COL_VIS_OD] is not None: action["visibility"][f"od_{suffix}"] = is_true(row[COL_VIS_OD])
            if row[COL_VIS_EAN] is not None: action["visibility"][f"EAN-number_{suffix}"] = is_true(row[COL_VIS_EAN])
            if row[COL_VIS_DOST] is not None: action["visibility"][f"dostupnost_{suffix}"] = is_true(row[COL_VIS_DOST])
            
            build_plan["actions"].append(action)
        
        # Determine output directory
        if output_dir_override:
            dir_path = output_dir_override
        else:
            # Default to directory of the base path if no override is provided
            dir_path = os.path.dirname(base_path)
            
        json_name = f"build_page_{page_num}.json"
        full_path = os.path.join(dir_path, json_name)
        
        # Write the build plan to a JSON file
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(build_plan, f, indent=2, ensure_ascii=False)

def enrich_active_book():
    service = AutomationService()
    try:
        sheet_name = xw.books.active.sheets.active.name
        service.enrich_active_workbook(sheet_name)
    except Exception as e:
        try:
            # Attempt to display error in Excel status bar
            xw.apps.active.api.StatusBar = f"Error: {e}"
        except:
            # If status bar is not accessible, pass
            pass
