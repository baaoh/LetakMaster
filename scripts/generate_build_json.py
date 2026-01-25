import json
import sys
import os
import xlwings as xw

# Ensure we can import from app if needed, though mostly standalone
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def generate_build_json(excel_path, target_page):
    print(f"Generating Build JSON for Page {target_page}...")
    
    app = xw.App(visible=False)
    try:
        book = app.books.open(excel_path)
        sheet = book.sheets["04.02 - 10.02"]
        
        last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
        # Read A to AY (Index 50)
        data = sheet.range(f"A7:AY{last_row}").value
        
        build_plan = {
            "page": target_page,
            "actions": []
        }
        
        # Column Indices
        COL_ALLOC = 38
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
        
        COL_HERO = 11
        COL_PAGE = 21
        
        for row in data:
            if not row: continue
            
            page = row[COL_PAGE]
            if page != target_page:
                continue
                
            psd_group = row[COL_ALLOC]
            if not psd_group:
                print(f"Skipping row on page {page} with no allocation.")
                continue
                
            hero = row[COL_HERO]
            
            # Action Object
            action = {
                "group": psd_group,
                "hero": hero,
                "data": {},
                "visibility": {}
            }
            
            suffix = psd_group.split('_')[1]
            
            def get_str(idx):
                val = row[idx]
                if val is None: return ""
                if isinstance(val, float) and val.is_integer():
                    return str(int(val))
                return str(val)

            # Data Mapping
            if row[COL_NAZEV_A]: action["data"][f"nazev_{suffix}A"] = get_str(COL_NAZEV_A)
            if row[COL_NAZEV_B]: action["data"][f"nazev_{suffix}B"] = get_str(COL_NAZEV_B)
            
            if row[COL_CENA_A]: action["data"][f"cena_{suffix}A"] = get_str(COL_CENA_A)
            if row[COL_CENA_B]: action["data"][f"cena_{suffix}B"] = get_str(COL_CENA_B)
            
            if row[COL_OD]: action["data"][f"od_{suffix}"] = get_str(COL_OD)
            
            if row[COL_EAN_NUM]: action["data"][f"EAN-number_{suffix}"] = get_str(COL_EAN_NUM)
            if row[COL_EAN_LBL]: action["data"][f"EAN:_{suffix}"] = get_str(COL_EAN_LBL)
            
            if row[COL_DOSTUPNOST]: action["data"][f"dostupnost_{suffix}"] = get_str(COL_DOSTUPNOST)
            
            # Visibility Mapping
            # Excel stores "TRUE"/"FALSE" strings or bools
            
            def is_true(val):
                return str(val).upper() == "TRUE"

            # Od
            if row[COL_VIS_OD] is not None:
                action["visibility"][f"od_{suffix}"] = is_true(row[COL_VIS_OD])
                
            # EAN Number
            if row[COL_VIS_EAN] is not None:
                action["visibility"][f"EAN-number_{suffix}"] = is_true(row[COL_VIS_EAN])
                
            # Dostupnost
            if row[COL_VIS_DOST] is not None:
                action["visibility"][f"dostupnost_{suffix}"] = is_true(row[COL_VIS_DOST])
            
            build_plan["actions"].append(action)
            
        output_path = f"build_page_{target_page}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(build_plan, f, indent=2, ensure_ascii=False)
            
        print(f"Saved build plan to {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        app.quit()

if __name__ == "__main__":
    target = 25
    if len(sys.argv) > 1:
        target = int(sys.argv[1])
    generate_build_json("Work_Letak_2026_v2.xls", target)
