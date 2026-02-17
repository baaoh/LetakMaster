import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.qa.qa_service import QAService
from app.database import ProjectState

def test_qa_service_init():
    # Mock DB Session
    mock_db = MagicMock()
    
    # Mock ProjectState query result
    mock_state = MagicMock()
    mock_state.id = 1
    mock_state.last_workspace_path = "dummy.xlsx"
    
    # Setup query return values
    # db.query(ProjectState).order_by(...).first() -> mock_state
    mock_query = mock_db.query.return_value
    mock_query.order_by.return_value.first.return_value = mock_state
    mock_query.get.return_value = mock_state
    
    # Mock AppConfig for password
    # db.query(AppConfig).filter_by(...).first()
    # We can just let it return None (default)
    
    service = QAService(mock_db)
    
    assert service.excel_path == "dummy.xlsx"
    assert service.state_id == 1
    assert os.path.exists(service.scans_dir)

@patch('app.qa.qa_service.PSDReader')
def test_import_flow(mock_reader_cls):
    # Mock DB
    mock_db = MagicMock()
    mock_state = MagicMock()
    mock_state.id = 1
    mock_state.last_workspace_path = "dummy.xlsx"
    mock_state.last_build_plans_path = "dummy_plans"
    
    mock_query = mock_db.query.return_value
    mock_query.order_by.return_value.first.return_value = mock_state
    mock_query.get.return_value = mock_state
    
    # Setup Mock Reader
    mock_reader = mock_reader_cls.return_value
    mock_reader.process_file.return_value = {
        "page": "Page_01",
        "json_path": "dummy.json",
        "preview_path": "dummy.png",
        "layer_count": 5
    }
    
    service = QAService(mock_db)
    
    # Mock json.load
    with patch('builtins.open', new_callable=MagicMock) as mock_open:
        with patch('json.load') as mock_json:
            mock_json.return_value = {
                "page_name": "Page 01",
                "layers": []
            }
            
            # Mock os.path.exists to allow build plan finding
            # QAService._find_build_plans_dir checks existence
            with patch('os.path.exists') as mock_exists:
                # We need side_effect to handle various checks
                def exists_side_effect(path):
                    if path == "dummy_plans": return True
                    if "build_page_1" in path: return True # plan exists
                    if path == "dummy.json": return True
                    if "scans" in path or "previews" in path: return True
                    return False
                
                mock_exists.side_effect = exists_side_effect
                
                # Mock QAMatcher
                service.matcher = MagicMock()
                service.matcher.match_page.return_value = {"Product_01": {"layers": {}}}
                
                # We must mock _write_actuals_to_excel or it will try to open Excel
                with patch.object(service, '_write_actuals_to_excel') as mock_write:
                    res = service.run_import(["test.psd"])
                    
                    assert len(res) == 1
                    # Ensure matching was called
                    service.matcher.match_page.assert_called()
                    # Ensure writing was called
                    mock_write.assert_called_once()