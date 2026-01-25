import sys
import os
import openpyxl

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.excel_service import ExcelService

def reproduce_external_links():
    # 1. Create a dummy Excel with external link
    test_file = "tests/temp_external_link.xlsx"
    if os.path.exists(test_file):
        os.remove(test_file)
        
    wb = openpyxl.Workbook()
    ws = wb.active
    # Create an external link? openpyxl makes this hard to forge manually without a real file.
    # But we can try to inspect what's happening.
    
    # Actually, the error is "externalLink1.xml". This suggests the source file had links.
    # We need to strip them.
    
    wb.save(test_file)
    wb.close()
    
    print("Dummy file created.")
    
    # 2. Run Deep Clean and see if we can strip external links
    service = ExcelService()
    
    # We will modify the deep clean function to also look for external links
    wb = openpyxl.load_workbook(test_file)
    # Check for external links
    # In openpyxl, these are usually in wb._external_links (private) or similar
    
    print(f"External links before: {getattr(wb, 'external_links', 'Unknown')}")
    
    wb.close()

if __name__ == "__main__":
    reproduce_external_links()
