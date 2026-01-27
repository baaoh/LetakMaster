import openpyxl
import os

def clean_excel(file_path, target_page):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        wb = openpyxl.load_workbook(file_path)
        sheet = wb.active
        
        # Columns (0-indexed logic)
        COL_ALLOC = 24 # X (1-based: 24)
        page_col = 21 # V (1-based: 22)
        
        print(f"Cleaning A4 Groups from Page {target_page} in {file_path}...")
        
        cleaned_count = 0
        for row in sheet.iter_rows(min_row=7):
            # Check Page
            try:
                if str(row[21].value).strip() == str(target_page):
                    alloc_val = row[23].value # X is 24th column, index 23
                    if alloc_val and str(alloc_val).startswith("A4_Grp"):
                        row[23].value = None # Clear Allocation
                        cleaned_count += 1
            except:
                pass

        wb.save(file_path)
        print(f"Cleaned {cleaned_count} rows. File saved.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clean_excel(r"D:\TAMDA\LetakMaster\workspaces\state_1\Workspace_State_1.xlsx", 43)
