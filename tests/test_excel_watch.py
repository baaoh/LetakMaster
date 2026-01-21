import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app.excel_service import ExcelService

def test_calculate_hash():
    service = ExcelService()
    file_path = "tests/sample.xlsx"
    
    # Ensure sample exists (re-create if needed, but it should be there from prev track)
    if not os.path.exists(file_path):
        import xlwings as xw
        app = xw.App(visible=False)
        wb = xw.Book()
        sheet = wb.sheets[0]
        sheet.range('A6').value = ['Product', 'Price']
        sheet.range('A7').value = ['Apple', 10]
        wb.save(file_path)
        wb.close()
        app.quit()

    hash1 = service.calculate_hash(file_path, sheet_name="Sheet1")
    assert hash1 is not None
    assert len(hash1) == 64 # SHA-256

def test_parse_sheet_by_name():
    service = ExcelService()
    file_path = "tests/sample.xlsx"
    
    # We assume 'Sheet1' is the default name created by xlwings/Excel
    data = service.parse_file(file_path, header_row=6, sheet_name="Sheet1")
    assert len(data) > 0
    assert data[0]["Product"]["value"] == "Apple"
