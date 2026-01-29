import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.qa.qa_service import QAService

def test_qa_service_init():
    service = QAService("dummy.xlsx")
    assert service.excel_path == "dummy.xlsx"
    assert os.path.exists(service.scans_dir)

@patch('app.qa.qa_service.PSDReader')
def test_import_flow(mock_reader_cls):
    # Setup Mock
    mock_reader = mock_reader_cls.return_value
    mock_reader.process_file.return_value = {
        "page": "Page_01",
        "json_path": "dummy.json",
        "preview_path": "dummy.png",
        "group_count": 5
    }
    
    service = QAService("dummy.xlsx")
    
    # Mock json.load to avoid file IO error
    with patch('builtins.open', new_callable=MagicMock) as mock_open:
        with patch('json.load') as mock_json:
            mock_json.return_value = {
                "page_name": "Page 01",
                "groups": { "Product_01": {"layers": {}} }
            }
            
            # Run
            # We must mock _write_actuals_to_excel or it will try to open Excel
            with patch.object(service, '_write_actuals_to_excel') as mock_write:
                res = service.run_import(["test.psd"])
                
                assert len(res) == 1
                mock_write.assert_called_once()
