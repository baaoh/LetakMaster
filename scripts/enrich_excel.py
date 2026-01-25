import xlwings as xw
import sys
import os
import re

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.allocation_logic import SlotAllocator

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

    # Destination Columns (Start at AM -> Index 38)
    # AM (38): PSD_Group
    # AN (39): PSD_Nazev_A
    # AO (40): PSD_Nazev_B
    # AP (41): PSD_EAN_Number
    # AQ (42): PSD_EAN_Label
    # AR (43): PSD_Dostupnost
    # AS (44): PSD_Od
    # AT (45): PSD_Cena_A
    # AU (46): PSD_Cena_B
    # AV (47): PSD_Obraz
    # AW (48): PSD_Vis_Od
    # AX (49): PSD_Vis_EAN_Num
    # AY (50): PSD_Vis_Dostupnost
    
    HEADERS = [
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
        
        # Read source data (A to Y)
        data_range = sheet.range(f"A7:Y{last_row}").value
        
        output_data = [[None] * len(HEADERS) for _ in range(len(data_range))]
        pages = {} 
        
        for r_offset, row in enumerate(data_range):
            if not row: continue
            
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

        for page_num in sorted(pages.keys()):
            products = pages[page_num]
            total_hero = sum(p['hero'] for p in products)
            
            if total_hero != 16:
                continue

            try:
                results = allocator.allocate(products)
                for res in results:
                    idx = int(res['product_id'].split('_')[1])
                    src_row = data_range[idx]
                    
                    # AM: Group
                    psd_group = f"Product_{res['start_slot']:02d}"
                    output_data[idx][0] = psd_group
                    
                    # AN: Nazev A (D)
                    output_data[idx][1] = str(src_row[COL_PRODUCT]) if src_row[COL_PRODUCT] else ""
                    
                    # AO: Nazev B (E + F)
                    desc = str(src_row[COL_DESC]) if src_row[COL_DESC] else ""
                    gram = str(src_row[COL_GRAMAZ]) if src_row[COL_GRAMAZ] else ""
                    output_data[idx][2] = f"{desc} {gram}".strip()
                    
                    # AP: EAN Number (B) - Text, handle 0
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
                    
                    # AQ: EAN Label (G)
                    lbl_in = str(src_row[COL_EANY_LBL]).lower().strip() if src_row[COL_EANY_LBL] else ""
                    lbl_out = EAN_LABEL_MAP.get(lbl_in, "EAN:")
                    if "více" in lbl_in: lbl_out = "Více druhů"
                    output_data[idx][4] = lbl_out
                    
                    # AR: Dostupnost (P, Q, Y)
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
                    if p0 and q0 and y0:
                        msg = "•pouze dostupné v Praze"
                    elif p0 and q0:
                        msg = "•není dostupné v Brně, Ústí"
                    elif p0:
                        msg = "•není dostupné v Brně"
                    elif q0:
                        msg = "•není dostupné v Ústí"
                    elif y0:
                        msg = "•není dostupné na TDE"
                        
                    output_data[idx][5] = msg
                    
                    # AS: Od
                    output_data[idx][6] = "od"
                    
                    # AT, AU: Cena (H/ACS)
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
                    
                    # AV: Obraz (K/Int. Kod)
                    output_data[idx][9] = str(src_row[COL_INT_KOD]) if src_row[COL_INT_KOD] else ""
                    
                    # --- VISIBILITY LOGIC ---
                    
                    # AW: Vis Od (Hide if W/Price is empty)
                    vis_od = "TRUE"
                    # Note: We used COL_PRICE (W) for this check, but mapped Price value from COL_ACS (H)
                    # User request: "IF W has nothing, hide PSD_Od"
                    val_w = src_row[COL_PRICE]
                    if val_w is None or str(val_w).strip() == "":
                        vis_od = "FALSE"
                    output_data[idx][10] = vis_od
                    
                    # AX: Vis EAN Num (Hide if Label != EAN:)
                    vis_ean = "TRUE"
                    if lbl_out != "EAN:":
                        vis_ean = "FALSE"
                    output_data[idx][11] = vis_ean
                    
                    # AY: Vis Dostupnost (Hide if default)
                    vis_dost = "TRUE"
                    if msg == "•dostupné na všech pobočkách":
                        vis_dost = "FALSE"
                    output_data[idx][12] = vis_dost

            except Exception as e:
                print(f"  Page {page_num} Error: {e}")

        # Write Headers
        sheet.range("AM6").value = HEADERS
        
        # Write Data
        print("Writing enriched data columns (AM-AY)...")
        sheet.range(f"AM7").value = output_data
        
        book.save()
        print("Enrichment Complete.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        app.quit()

if __name__ == "__main__":
    enrich_excel("Work_Letak_2026_v2.xls", "04.02 - 10.02")