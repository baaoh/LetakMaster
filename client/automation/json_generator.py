import xlwings as xw
import os
import json
from datetime import datetime

class JsonGenerator:
    """Generates Photoshop instruction files from Excel layouts."""
    def run_export(self):
        try:
            book = xw.books.active; sheet = book.sheets.active
            timestamp = datetime.now().strftime("%y%m%d_%H%M")
            folder_name = f"{timestamp}_{book.name.split('.')[0]}"
            output_dir = os.path.join(os.getcwd(), "workspaces", "build_plans", folder_name)
            os.makedirs(output_dir, exist_ok=True)
            
            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
            data = sheet.range(f"A7:AY{last_row}").options(ndim=2).value
            
            pages_data = {}
            for row in data:
                try:
                    p = int(float(row[21]))
                    if p not in pages_data: pages_data[p] = []
                    pages_data[p].append(row)
                except: continue

            for page_num, rows in pages_data.items():
                self._write_page_json(page_num, rows, output_dir)

            return {"status": "success", "message": f"Exported to {folder_name}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _write_page_json(self, page_num, rows, output_dir):
        COL_HERO = 11; COL_ALLOC = 38; COL_NAZEV_A = 39; COL_NAZEV_B = 40; COL_EAN_NUM = 41; COL_EAN_LBL = 42; COL_DOSTUPNOST = 43; COL_OD = 44; COL_CENA_A = 45; COL_CENA_B = 46; COL_OBRAZ = 47; COL_VIS_OD = 48; COL_VIS_EAN = 49; COL_VIS_DOST = 50
        build_plan = {"page": page_num, "actions": []}
        
        def get_str(row, idx):
            if idx >= len(row): return ""
            val = row[idx]
            if val is None: return ""
            if isinstance(val, float) and val.is_integer(): return str(int(val))
            return str(val)
            
        def is_true(row, idx):
            if idx >= len(row): return False
            return str(row[idx]).upper() == "TRUE"

        for row in rows:
            if len(row) <= COL_ALLOC or not row[COL_ALLOC]: continue
            psd_group = row[COL_ALLOC]
            if psd_group.startswith("A4_Grp_") and row[COL_VIS_DOST] is None: continue
            
            action = {"group": psd_group, "hero": row[COL_HERO], "data": {}, "visibility": {}}
            try:
                parts = psd_group.split('_')
                suffix = parts[2] if psd_group.startswith("A4_Grp_") else parts[1]
            except: suffix = "XX"

            if row[COL_NAZEV_A]: action["data"][f"nazev_{suffix}A"] = get_str(row, COL_NAZEV_A)
            if row[COL_NAZEV_B]:
                action["data"][f"nazev_{suffix}B"] = get_str(row, COL_NAZEV_B)
                action["visibility"][f"nazev_{suffix}B"] = True
            else: action["visibility"][f"nazev_{suffix}B"] = False

            if row[COL_CENA_A]: 
                action["data"][f"cena_{suffix}A"] = get_str(row, COL_CENA_A)
                price_b = get_str(row, COL_CENA_B)
                if not price_b or price_b == "0": price_b = "00"
                action["data"][f"cena_{suffix}B"] = price_b

            if row[COL_OD]: action["data"][f"od_{suffix}"] = get_str(row, COL_OD)
            if row[COL_EAN_NUM]: action["data"][f"EAN-number_{suffix}"] = get_str(row, COL_EAN_NUM)
            if row[COL_EAN_LBL]: action["data"][f"EAN:_{suffix}"] = get_str(row, COL_EAN_LBL)
            if row[COL_DOSTUPNOST]: action["data"][f"dostupnost_{suffix}"] = get_str(row, COL_DOSTUPNOST)
            if row[COL_OBRAZ]: action["data"][f"image_{suffix}"] = get_str(row, COL_OBRAZ)

            if row[COL_VIS_OD] is not None: action["visibility"][f"od_{suffix}"] = is_true(row, COL_VIS_OD)
            if row[COL_VIS_EAN] is not None: action["visibility"][f"EAN-number_{suffix}"] = is_true(row, COL_VIS_EAN)
            if row[COL_VIS_DOST] is not None: action["visibility"][f"dostupnost_{suffix}"] = is_true(row, COL_VIS_DOST)
            build_plan["actions"].append(action)

        with open(os.path.join(output_dir, f"build_page_{page_num}.json"), 'w', encoding='utf-8') as f:
            json.dump(build_plan, f, indent=2, ensure_ascii=False)
