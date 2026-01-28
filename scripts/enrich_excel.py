import xlwings as xw
import sys
import os
import re

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.allocation_logic import SlotAllocator
from app.clustering import ProductClusterer

def clean_int_code(val):
    if not val:
        return ""
    s_val = str(val)
    # Handle multiline
    parts = s_val.split('\n')
    cleaned_parts = []
    for p in parts:
        p = p.strip()
        if not p: continue
        try:
            f = float(p)
            if f.is_integer():
                cleaned_parts.append(str(int(f)))
            else:
                cleaned_parts.append(p)
        except ValueError:
            cleaned_parts.append(p)
    return "\n".join(cleaned_parts)

def enrich_excel(file_path, sheet_name):
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
    
    # Read AL (37) and AM (38)
    COL_STATUS = 37
    COL_EXISTING_GROUP = 38

    # Destination Columns (Start at AL -> Index 37)
    HEADERS = [
        "PSD_Status", 
        "PSD_Group", 
        "PSD_Nazev_A", 
        "PSD_Nazev_B", 
        "PSD_EAN_Number", 
        "PSD_EAN_Label", 
        "PSD_Dostupnost", 
        "PSD_Od", 
        "PSD_Cena_A", 
        "PSD_Cena_B", 
        "PSD_Obraz",
        "PSD_Vis_Od",
        "PSD_Vis_EAN_Num",
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

    app = xw.App(visible=False)
    try:
        print(f"Opening {file_path}...")
        book = app.books.open(file_path)
        sheet = book.sheets[sheet_name]
        
        last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
        if last_row < 7:
            print("No data found.")
            return

        print(f"Scanning rows 7 to {last_row}...")
        
        # Expand read range to include AL and AM
        data_range = sheet.range(f"A7:AM{last_row}").value
        color_range = sheet.range(f"H7:H{last_row}")
        
        try:
            h_colors = [cell.color for cell in color_range]
        except Exception as e:
            print(f"Color Fetch Fallback active due to: {e}")
            h_colors = [None] * len(data_range)
        
        output_data = [[None] * len(HEADERS) for _ in range(len(data_range))]
        pages = {} 
        
        for r_offset, row in enumerate(data_range):
            if not row: continue
            
            hero = row[COL_HERO]
            page = row[COL_PAGE]
            product = row[COL_PRODUCT]
            
            # Read existing group and status
            existing_group = ""
            status_marker = ""
            
            if len(row) > COL_EXISTING_GROUP:
                existing_group = str(row[COL_EXISTING_GROUP]).strip() if row[COL_EXISTING_GROUP] else ""
            if len(row) > COL_STATUS:
                status_marker = str(row[COL_STATUS]).strip() if row[COL_STATUS] else ""
            
            if page is not None and hero is not None:
                try:
                    h_val = int(float(hero))
                    p_val = int(float(page))
                    if p_val not in pages: pages[p_val] = []
                    
                    # Extract Price and Weight for Clustering
                    raw_price = row[COL_PRICE]
                    if not raw_price: raw_price = row[COL_ACS] # Fallback to ACS
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
                        'weight_text': str(raw_weight) if raw_weight else "",
                        'existing_group': existing_group,
                        'status_marker': status_marker
                    })
                except:
                    pass

        allocator = SlotAllocator()
        clusterer = ProductClusterer()

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
                        
                        # Index 0 is Status, 1 is Group
                        output_data[idx][0] = None # Auto
                        output_data[idx][1] = psd_group
                        
                        output_data[idx][2] = str(src_row[COL_PRODUCT]) if src_row[COL_PRODUCT] else ""
                        
                        desc = str(src_row[COL_DESC]) if src_row[COL_DESC] else ""
                        gram = str(src_row[COL_GRAMAZ]) if src_row[COL_GRAMAZ] else ""
                        if desc and gram: output_data[idx][3] = f"{desc}\n{gram}".strip()
                        else: output_data[idx][3] = f"{desc}{gram}".strip()
                        
                        ean_raw = src_row[COL_EAN]
                        ean_str = ""
                        if ean_raw is not None:
                            if isinstance(ean_raw, float): ean_str = str(int(ean_raw))
                            else: ean_str = str(ean_raw)
                        output_data[idx][4] = "'" + ean_str[-6:] if len(ean_str) > 6 else "'" + ean_str
                        
                        lbl_in = str(src_row[COL_EANY_LBL]).lower().strip() if src_row[COL_EANY_LBL] else ""
                        lbl_out = EAN_LABEL_MAP.get(lbl_in, "EAN:")
                        if "více" in lbl_in: lbl_out = "Více druhů"
                        try:
                            val_num = int(float(lbl_in))
                            if 1 < val_num <= 4: lbl_out = f"{val_num} druhy" if val_num < 5 else f"{val_num} druhů"
                            elif val_num > 4: lbl_out = "Více druhů"
                        except: pass
                        output_data[idx][5] = lbl_out
                        
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
                        output_data[idx][6] = msg
                        output_data[idx][7] = "od"
                        
                        price_raw = src_row[COL_ACS]
                        p_int = ""; p_dec = ""
                        if price_raw is not None:
                            try:
                                f = float(str(price_raw).replace(',', '.'))
                                p_int = str(int(f))
                                dec_val = int(round((f - int(f)) * 100))
                                p_dec = f"{dec_val:02d}"
                            except: p_int = str(price_raw)
                        output_data[idx][8] = p_int
                        output_data[idx][9] = p_dec
                        
                        output_data[idx][10] = clean_int_code(src_row[COL_INT_KOD])
                        
                        val_w = src_row[COL_PRICE]
                        row_color = h_colors[idx] if idx < len(h_colors) else None
                        is_highlighted = row_color is not None and row_color != (255, 255, 255) and row_color != 16777215
                        
                        has_price_text = val_w is not None and str(val_w).strip() != ""
                        is_plural = lbl_out != "EAN:"
                        vis_od = "TRUE" if (is_highlighted and is_plural) or has_price_text else "FALSE"
                        output_data[idx][11] = vis_od
                        
                        vis_ean = "TRUE"
                        if lbl_out != "EAN:": vis_ean = "FALSE"
                        output_data[idx][12] = vis_ean
                        
                        vis_dost = "TRUE"
                        if msg == "•dostupné na všech pobočkách": vis_dost = "FALSE"
                        output_data[idx][13] = vis_dost

                except Exception as e:
                    print(f"  Page {page_num} Error: {e}")
            else:
                 # --- A4 / UNSTRUCTURED LOGIC (Fallback) ---
                print(f"Page {page_num}: Total Hero {total_hero} != {expected_hero}. Running Clustering Logic...")
                
                manual_items = []
                auto_items = []
                manual_pattern = re.compile(r"^(?:A4_Grp_)?([A-Za-z]+[\w\-]*)$", re.IGNORECASE)

                for p in products:
                    if not p['name'] or not p['name'].strip(): continue
                    
                    ex_grp = p['existing_group']
                    status = p['status_marker']
                    
                    is_manual = False
                    key = ""
                    
                    # 1. Check Explicit Manual Status
                    if status and status.upper() == "MANUAL":
                        is_manual = True
                        if ex_grp:
                            key = ex_grp.replace("A4_Grp_", "").replace("Product_", "")
                        else:
                            is_manual = False 
                    
                    # 2. Check Regex Pattern (if not already valid manual)
                    if not is_manual and ex_grp:
                        core_key = ex_grp.replace("A4_Grp_", "").replace("Product_", "")
                        if re.search(r'[A-Za-z]', core_key):
                            is_manual = True
                            key = core_key
                    
                    if is_manual and key:
                        p['manual_key'] = key
                        manual_items.append(p)
                    else:
                        auto_items.append(p)

                # Group Manual Items
                manual_groups = {}
                for m in manual_items:
                    k = m['manual_key']
                    if k not in manual_groups: manual_groups[k] = []
                    manual_groups[k].append(m)
                
                # Group Auto Items (Clustering)
                auto_groups = clusterer.group_items(auto_items)
                
                print(f"  -> Manual Groups: {len(manual_groups)}, Auto Groups: {len(auto_groups)}")
                
                final_groups = []
                for key, grp in manual_groups.items():
                    final_groups.append({
                        "id": f"A4_Grp_{key}", 
                        "items": grp,
                        "is_manual": True
                    })
                for i, grp in enumerate(auto_groups, 1):
                    final_groups.append({
                        "id": f"A4_Grp_{i:02d}", 
                        "items": grp,
                        "is_manual": False
                    })
                
                for group_obj in final_groups:
                    group_id_str = group_obj["id"]
                    grp = group_obj["items"]
                    is_manual_grp = group_obj["is_manual"]
                    leader_item = grp[0]
                    
                    # 1. Calculate Aggregates
                    grp_names = [x['name'] for x in grp]
                    nazev_a = clusterer.generate_smart_title(grp_names)
                    nazev_b = clusterer.generate_variants(grp, nazev_a)
                    
                    if len(nazev_a) > 20:
                        split_idx = nazev_a[:21].rfind(' ')
                        if split_idx == -1: split_idx = 20
                        part_a = nazev_a[:split_idx].strip()
                        part_b = nazev_a[split_idx:].strip()
                        nazev_a = part_a
                        nazev_b = f"{part_b}, {nazev_b}" if nazev_b else part_b
                    
                    prices = [x['price'] for x in grp if x['price'] > 0]
                    min_price = min(prices) if prices else 0.0
                    has_multiple_prices = len(set(prices)) > 1
                    
                    count = len(grp)
                    label = "EAN:" if count == 1 else (f"{count} druhy" if count <= 4 else "více druhů")
                    
                    p_int = ""; p_dec = ""
                    if min_price > 0:
                        try:
                            price_float = float(min_price)
                            p_int = str(int(price_float))
                            dec_val = int(round((price_float - int(price_float)) * 100))
                            p_dec = f"{dec_val:02d}"
                        except Exception as e: 
                            p_int = str(min_price)
                    
                    img_codes = []
                    for x in grp:
                        rx = data_range[x['offset']]
                        code = clean_int_code(rx[COL_INT_KOD])
                        if code: img_codes.append(code)
                    combined_img = "\n".join(img_codes)

                                        for item in grp:

                                            idx = item['offset']

                                            src_row = data_range[idx]

                                            

                                            if item == leader_item:

                                                output_data[idx][0] = "MANUAL" if is_manual_grp else None

                                                output_data[idx][1] = group_id_str

                                                

                                                output_data[idx][2] = nazev_a

                                                output_data[idx][3] = nazev_b

                                                output_data[idx][5] = label

                                                output_data[idx][8] = p_int

                                                output_data[idx][9] = p_dec

                                                

                                                vis_od = "TRUE" if (has_multiple_prices or count > 1) else "FALSE"

                                                output_data[idx][11] = vis_od

                                                output_data[idx][7] = "od"

                                                

                                                ean_raw = src_row[COL_EAN]

                                                ean_str = ""

                                                if ean_raw is not None:

                                                    if isinstance(ean_raw, float): ean_str = str(int(ean_raw))

                                                    else: ean_str = str(ean_raw)

                                                output_data[idx][4] = "'" + ean_str[-6:] if len(ean_str) > 6 else "'" + ean_str

                                                

                                                output_data[idx][10] = combined_img

                                                

                                                val_p = src_row[COL_BRNO]; val_q = src_row[COL_USTI]; val_y = src_row[COL_TDE]

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

                                                output_data[idx][6] = msg

                                                

                                                vis_ean = "TRUE"

                                                if label != "EAN:": vis_ean = "FALSE"

                                                output_data[idx][12] = vis_ean

                                                

                                                vis_dost = "FALSE" if msg == "•dostupné na všech pobočkách" else "TRUE"

                                                output_data[idx][13] = vis_dost

                                            else:

                                                # Slave Item

                                                # 1. Write Group ID & Status to persist grouping

                                                output_data[idx][0] = "MANUAL" if is_manual_grp else None

                                                output_data[idx][1] = group_id_str 

                                                

                                                # 2. Write Raw Data for reference

                                                output_data[idx][2] = str(src_row[COL_PRODUCT]) if src_row[COL_PRODUCT] else ""

                                                output_data[idx][3] = str(src_row[COL_DESC]) if src_row[COL_DESC] else ""

                                                output_data[idx][10] = clean_int_code(src_row[COL_INT_KOD])

                                                

                                                # 3. Explicitly Clear Aggregated Columns

                                                output_data[idx][4] = None

                                                output_data[idx][5] = None

                                                output_data[idx][6] = None

                                                output_data[idx][7] = None

                                                output_data[idx][8] = None

                                                output_data[idx][9] = None

                                                output_data[idx][11] = None

                                                output_data[idx][12] = None

                                                output_data[idx][13] = None

        # Write Headers to AL6
        sheet.range("AL6").value = HEADERS
        
        # Write Data to AL7
        print("Writing enriched data columns (AL-AY)...")
        sheet.range(f"AL7").value = output_data
        
        book.save()
        print("Enrichment Complete.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        app.quit()

if __name__ == "__main__":
    # Example usage
    enrich_excel("Work_Letak_2026_v2.xls", "04.02 - 10.02")