import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
from unittest.mock import MagicMock, patch
from app.sync_service import SyncService, DiffService
from app.database import AppConfig, ProjectState, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_diff_service():
    diff = DiffService()
    state_a = [{"Product": "Apple", "Price": 10}]
    state_b = [{"Product": "Apple", "Price": 12}] # Changed
    
    # We expect a simple diff format
    # This is a naive diff expectation, implementation can vary
    report = diff.compare(state_a, state_b, key_field="Product")
    assert report["modified"][0]["Product"] == "Apple"
    assert report["modified"][0]["changes"]["Price"]["old"] == 10
    assert report["modified"][0]["changes"]["Price"]["new"] == 12

def test_sync_service_no_change(db):
    # Setup Config
    db.add(AppConfig(key="master_excel_path", value="test.xlsx"))
    db.add(AppConfig(key="watched_sheet_name", value="Sheet1"))
    
    # Setup existing state
    existing_hash = "hash123"
    db.add(ProjectState(excel_hash=existing_hash, data_snapshot_json="[]", created_by="test"))
    db.commit()
    
    # Mock ExcelService
    with patch('app.sync_service.ExcelService') as MockExcel:
        service_mock = MockExcel.return_value
        service_mock.calculate_hash.return_value = "hash123" # Same hash
        
        sync = SyncService(db)
        result = sync.sync_now("user1")
        
        assert result["status"] == "no_change"
        service_mock.parse_file.assert_not_called()

def test_sync_service_change_detected(db):
    db.add(AppConfig(key="master_excel_path", value="test.xlsx"))
    db.add(AppConfig(key="watched_sheet_name", value="Sheet1"))
    db.commit()
    
    with patch('app.sync_service.ExcelService') as MockExcel:
        service_mock = MockExcel.return_value
        service_mock.calculate_hash.return_value = "new_hash_456"
        service_mock.parse_file.return_value = [{"col": "val"}]
        
        sync = SyncService(db)
        result = sync.sync_now("user1")
        
        assert result["status"] == "updated"
        
        # Verify DB
        new_state = db.query(ProjectState).filter_by(excel_hash="new_hash_456").first()
        assert new_state is not None
        assert new_state.created_by == "user1"
        assert json.loads(new_state.data_snapshot_json) == [{"col": "val"}]
