import xlwings as xw
import sys

def read_excel_data(file_path, sheet_name):
    try:
        app = xw.App(visible=False)
        book = app.books.open(file_path)
        sheet = book.sheets[sheet_name]
        
        # Read the range around row 195 (header might be above)
        # Assuming data starts around row 195. Let's read a block.
        # Column L is index 12 (if 1-based) -> 11 (0-based)
        # Column V is index 22 -> 21
        
        # Page 25 rows check
        # Page 19 was 195. 
        # Page 20 = 195 + 13? = 208
        # ...
        # Let's just scan column V (Page) to find rows for 25
        print(f"Scanning for Page 25...")
        
        # Read a larger chunk of 'Page' column (V)
        # Column V is index 21
        page_col = sheet.range('V1:V1000').value
        
        start_row = -1
        rows_data = []
        
        for i, val in enumerate(page_col):
            if val == 25:
                if start_row == -1:
                    start_row = i + 1 # 1-based Excel row
                
                # Get Product (C -> index 2) and Hero (L -> index 11)
                # Read row i+1
                # Optimizing: read row by row is slow, but safe for small data
                full_row = sheet.range(f'A{i+1}:V{i+1}').value
                rows_data.append({
                    'row': i+1,
                    'hero': full_row[11],
                    'product': full_row[2]
                })
        
        if not rows_data:
            print("Page 25 not found in first 1000 rows.")
            return

        print(f"Found {len(rows_data)} items for Page 25:")
        total_hero = 0
        for r in rows_data:
            print(f"Row {r['row']}: Hero={r['hero']} | Product={r['product']}")
            try:
                total_hero += int(r['hero'])
            except: 
                pass
        
        print(f"Total Hero: {total_hero}")

        
    except Exception as e:
        print(f"Error: {e}")
        try:
            app.quit()
        except:
            pass

if __name__ == "__main__":
    read_excel_data("Copy of letak prodejna 2026 NEW FINAL.xls", "04.02 - 10.02")
