import xlwings as xw
import sys
import os

# Ensure we can import from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.allocation_logic import SlotAllocator

def inspect_page_19(file_path):
    app = xw.App(visible=False)
    try:
        book = app.books.open(file_path)
        sheet = book.sheets["04.02 - 10.02"]
        
        last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
        data_range = sheet.range(f"A7:V{last_row}").value
        
        # Extract Page 19
        p19_products = []
        for r_idx, row in enumerate(data_range):
            if not row: continue
            
            hero = row[11]
            page = row[21]
            product = row[2]
            
            if page == 19:
                 p19_products.append({
                        'id': f"Row_{r_idx+7}", # 1-based row
                        'hero': int(hero),
                        'product': product
                    })
        
        print(f"Page 19 Items: {len(p19_products)}")
        for p in p19_products:
            print(f"- {p['id']}: Hero {p['hero']} ({p['product']})")
            
        allocator = SlotAllocator()
        print("\n--- Running Allocation ---")
        try:
            results = allocator.allocate(p19_products)
            print("\nFinal Allocation for Page 19:")
            print(f"{ 'Product':<10} | { 'Hero':<5} | { 'Start Slot':<10} | {'Covered'}")
            for res in results:
                # Sort by start slot for visualization
                print(f"{res['product_id']:<10} | {res['hero']:<5} | {res['start_slot']:<10} | {res['covered_slots']}")
                
        except Exception as e:
            print(f"Allocation Failed: {e}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        app.quit()

if __name__ == "__main__":
    inspect_page_19("Copy of letak prodejna 2026 NEW FINAL.xls")
