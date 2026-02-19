import xlwings as xw
import re
from typing import List, Dict, Optional
from core.allocation.slot_allocator import SlotAllocator
from core.clustering.clusterer import ProductClusterer

class LayoutEngine:
    """The 'Brain' that calculates Grid and A4 layouts."""
    def __init__(self):
        self.clusterer = ProductClusterer()
        self.allocator = SlotAllocator()

    def clean_int_code(self, val):
        if not val: return ""
        s_val = str(val)
        parts = s_val.split('\n')
        cleaned_parts = []
        for p in parts:
            p = p.strip()
            if not p: continue
            try:
                f = float(p)
                if f.is_integer(): cleaned_parts.append(str(int(f)))
                else: cleaned_parts.append(p)
            except: cleaned_parts.append(p)
        return "\n".join(cleaned_parts)

    def run_enrichment(self):
        try:
            book = xw.books.active; sheet = book.sheets.active
            COL_EAN = 1; COL_PRODUCT = 3; COL_DESC = 4; COL_GRAMAZ = 5; COL_EANY_LBL = 6; COL_ACS = 7; COL_INT_KOD = 10; COL_HERO = 11; COL_BRNO = 15; COL_USTI = 16; COL_PAGE = 21; COL_PRICE = 22; COL_TDE = 24
            COL_STATUS = 37; COL_EXISTING_GROUP = 38
            HEADERS = ["PSD_Status", "PSD_Group", "PSD_Nazev_A", "PSD_Nazev_B", "PSD_EAN_Number", "PSD_EAN_Label", "PSD_Dostupnost", "PSD_Od", "PSD_Cena_A", "PSD_Cena_B", "PSD_Obraz", "PSD_Vis_Od", "PSD_Vis_EAN_Num", "PSD_Vis_Dostupnost"]
            EAN_MAP = {"ean": "EAN:", "ean více druhů": "Více druhů", "ean 2 druhy": "2 druhy", "ean 3 druhy": "3 druhy", "ean 4 druhy": "4 druhy", "1": "EAN:", "2": "2 druhy", "3": "3 druhy", "4": "4 druhy", "všechny": "Všechny druhy", "vše": "Všechny druhy", "více": "Více druhů", "více druhů": "Více druhů"}

            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
            if last_row < 7: return {"status": "error", "message": "No data found."}

            data_range = sheet.range(f"A7:AM{last_row}").options(ndim=2).value
            color_range = sheet.range(f"H7:H{last_row}")
            try: h_colors = [cell.color for cell in color_range]
            except: h_colors = [None] * len(data_range)

            output_data = [[None for _ in range(14)] for _ in range(len(data_range))]
            pages = {}

            for r_idx, row in enumerate(data_range):
                if not row or len(row) <= COL_PAGE: continue
                raw_page, raw_hero, raw_product, raw_ean = row[COL_PAGE], row[COL_HERO], row[COL_PRODUCT], row[COL_EAN]
                if raw_page is None: continue 
                try:
                    p_num = int(float(raw_page))
                    if p_num not in pages: pages[p_num] = []
                    h_val = 0
                    if raw_hero is not None:
                        try:
                            v = int(float(raw_hero))
                            if v in [1, 2, 4]: h_val = v
                        except: pass
                    p_name, p_ean = str(raw_product).strip() if raw_product else "", str(raw_ean).strip() if raw_ean else ""
                    if not p_name and not p_ean and h_val == 0: continue
                    raw_p = row[COL_PRICE] or row[COL_ACS]; price_val = 0.0
                    if raw_p:
                        try: price_val = float(str(raw_p).replace(',', '.'))
                        except: pass
                    pages[p_num].append({'id': f"Idx_{r_idx}", 'offset': r_idx, 'hero': h_val, 'name': p_name if p_name else "!!! MISSING NAME !!!", 'price': price_val, 'weight_text': str(row[COL_GRAMAZ] or ""), 'existing_group': str(row[COL_EXISTING_GROUP] or "").strip() if len(row) > COL_EXISTING_GROUP else "", 'status_marker': str(row[COL_STATUS] or "").strip() if len(row) > COL_STATUS else ""})
                except: continue

            for p_num in sorted(pages.keys()):
                products = pages[p_num]; total_hero = sum(p['hero'] for p in products); expected_hero = 8 if p_num == 1 else 16
                if total_hero == expected_hero:
                    valid_items = [p for p in products if p['hero'] > 0]
                    results = self.allocator.allocate(valid_items)
                    for res in results:
                        off = int(res['item_id'].split('_')[1]); suffix = "_K" if res['hero'] == 2 else ("_EX" if res['hero'] == 4 else "")
                        output_data[off] = self._map_standard_row(data_range[off], f"Product_{res['start_slot']:02d}{suffix}", h_colors[off], EAN_MAP)
                else:
                    manual_items, auto_items = [], []
                    for p in products:
                        is_manual = (p['status_marker'].upper() == "MANUAL" or re.search(r'[A-Za-z]', p['existing_group'].replace("A4_Grp_", "").replace("Product_", "")))
                        if is_manual and p['existing_group']: p['manual_key'] = p['existing_group'].replace("A4_Grp_", "").replace("Product_", ""); manual_items.append(p)
                        else: auto_items.append(p)
                    manual_groups = {}
                    for m in manual_items:
                        k = m['manual_key']
                        if k not in manual_groups: manual_groups[k] = []
                        manual_groups[k].append(m)
                    auto_groups = self.clusterer.group_items(auto_items); final_groups = []
                    for key, grp in manual_groups.items(): final_groups.append({"id": f"A4_Grp_{key}", "items": grp, "is_manual": True})
                    for i, grp in enumerate(auto_groups, 1): final_groups.append({"id": f"A4_Grp_{i:02d}", "items": grp, "is_manual": False})
                    for group_obj in final_groups:
                        group_id, grp, leader = group_obj["id"], group_obj["items"], group_obj["items"][0]
                        names = [x['name'] for x in grp]; nazev_a = self.clusterer.generate_smart_title(names); nazev_b = self.clusterer.generate_variants(grp, nazev_a)
                        if len(nazev_a) > 20:
                            split_idx = nazev_a[:21].rfind(' ')
                            if split_idx == -1: split_idx = 20
                            part_a, part_b = nazev_a[:split_idx].strip(), nazev_a[split_idx:].strip()
                            nazev_a, nazev_b = part_a, f"{part_b}, {nazev_b}" if nazev_b else part_b
                        prices = [x['price'] for x in grp if x['price'] > 0]; has_multiple = len(set(prices)) > 1; label = "EAN:" if len(grp) == 1 else (f"{len(grp)} druhy" if len(grp) <= 4 else "více druhů")
                        off = leader['offset']; row = self._map_standard_row(data_range[off], group_id, h_colors[off], EAN_MAP)
                        row[0] = "MANUAL" if group_obj["is_manual"] else None; row[2], row[3], row[5] = nazev_a, nazev_b, label
                        if has_multiple: row[11] = "TRUE"
                        elif row[11] != "TRUE": row[11] = "FALSE"
                        img_codes = []
                        for x in grp:
                            code = self.clean_int_code(data_range[x['offset']][10])
                            if code: img_codes.append(code)
                        row[10] = "\n".join(img_codes); output_data[off] = row
                        for slave in grp[1:]:
                            s_off = slave['offset']; s_src = data_range[s_off]; s_row = [None] * 14; s_row[0], s_row[1] = row[0], group_id; s_row[2], s_row[3] = str(s_src[COL_PRODUCT] or ""), str(s_src[COL_DESC] or ""); s_row[10] = self.clean_int_code(s_src[10]); output_data[s_off] = s_row
            sheet.range("AL6").value = HEADERS; sheet.range("AL7").value = output_data
            return {"status": "success", "message": "Layouts calculated."}
        except Exception as e:
            import traceback; print(traceback.format_exc()); return {"status": "error", "message": str(e)}

    def _map_standard_row(self, src, psd_group, color, ean_map):
        COL_EAN = 1; COL_PRODUCT = 3; COL_DESC = 4; COL_GRAMAZ = 5; COL_EANY_LBL = 6; COL_ACS = 7; COL_INT_KOD = 10; COL_BRNO = 15; COL_USTI = 16; COL_PRICE = 22; COL_TDE = 24
        row = [None] * 14; row[1] = psd_group; row[2] = str(src[COL_PRODUCT] or "") if src[COL_PRODUCT] else "!!! MISSING NAME !!!"
        desc = str(src[COL_DESC] or "").strip(); gram = str(src[COL_GRAMAZ] or "").strip(); row[3] = f"{desc}\n{gram}" if desc and gram else f"{desc}{gram}"
        ean = str(src[COL_EAN] or ""); row[4] = "'" + ean[-6:] if len(ean) > 6 else "'" + ean
        val_g = src[COL_EANY_LBL]; lbl_in = ""
        if val_g is not None:
            if isinstance(val_g, float) and val_g.is_integer(): lbl_in = str(int(val_g))
            else: lbl_in = str(val_g).lower().strip()
        row[5] = ean_map.get(lbl_in, "EAN:")
        if "více" in lbl_in: row[5] = "Více druhů"
        if not lbl_in: row[5] = "EAN:"
        p0 = (src[COL_BRNO] == 0); q0 = (src[COL_USTI] == 0); y0 = (src[COL_TDE] == 0); msg = "•dostupné na všech pobočkách"
        if p0 and q0 and y0: msg = "•pouze dostupné v Praze"
        elif p0 and q0: msg = "•není dostupné v Brně, Ústí"
        elif p0: msg = "•není dostupné v Brně"
        elif q0: msg = "•není dostupné v Ústí"
        elif y0: msg = "•není dostupné na TDE"
        row[6] = msg; row[7] = "od"; price = src[COL_ACS] or 0
        try:
            f_p = float(str(price).replace(',', '.')); row[8] = str(int(f_p)); row[9] = f"{int(round((f_p % 1) * 100)):02d}"
        except: row[8] = str(price); row[9] = "00"
        row[10] = self.clean_int_code(src[10]); is_highlighted = color is not None and color != (255, 255, 255) and color != 16777215; has_price_text = src[COL_PRICE] is not None and str(src[COL_PRICE]).strip() != ""
        is_singular = (row[5] == "EAN:"); row[11] = "TRUE" if (is_highlighted and not is_singular) or has_price_text else "FALSE"; row[12] = "TRUE" if is_singular else "FALSE"; row[13] = "FALSE" if msg == "•dostupné na všech pobočkách" else "TRUE"
        return row
