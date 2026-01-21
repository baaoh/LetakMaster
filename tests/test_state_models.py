import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, AppConfig, ProjectState

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

def test_app_config(db):
    # Test Singleton-like behavior or simple key-value
    conf = AppConfig(key="master_excel_path", value="C:/Data/Master.xlsx")
    db.add(conf)
    db.commit()
    
    fetched = db.query(AppConfig).filter_by(key="master_excel_path").first()
    assert fetched.value == "C:/Data/Master.xlsx"

def test_project_state(db):
    # Test storing a large JSON blob
    large_data = [{"col1": i, "col2": f"val{i}"} for i in range(100)]
    state = ProjectState(
        excel_hash="abc123hash",
        data_snapshot_json=json.dumps(large_data),
        created_by="admin"
    )
    db.add(state)
    db.commit()
    
    fetched = db.query(ProjectState).first()
    assert fetched.excel_hash == "abc123hash"
    loaded_data = json.loads(fetched.data_snapshot_json)
    assert len(loaded_data) == 100
    assert loaded_data[99]["col2"] == "val99"
