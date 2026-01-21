import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app.excel_service import ExcelService

def test_parse_sample_excel():
    service = ExcelService()
    # Path to the sample created in the previous step
    file_path = os.path.abspath("tests/sample.xlsx")
    
    # We expect a list of dicts, where each dict is a row
    data = service.parse_file(file_path, header_row=6)
    
    assert len(data) == 1
    row = data[0]
    
    assert row["Product"]["value"] == "Apple"
    assert row["Product"]["formatting"]["bold"] is True
    assert row["Product"]["formatting"]["color"] == "#ff0000"
    
    assert row["Price"]["value"] == 10.0
