import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

# Test Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_ingestion.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("test_ingestion.db"):
        os.remove("test_ingestion.db")

client = TestClient(app)

def test_upload_excel_endpoint():
    # Use the sample file from previous task
    file_path = "tests/sample.xlsx"
    with open(file_path, "rb") as f:
        response = client.post(
            "/upload/excel",
            files={"file": ("sample.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    
    assert response.status_code == 200
    assert "file_id" in response.json()
    
    # Verify DB content
    db = TestingSessionLocal()
    from app.database import SourceFile, SourceData
    source_file = db.query(SourceFile).first()
    assert source_file is not None
    assert source_file.filename == "sample.xlsx"
    
    data_points = db.query(SourceData).all()
    assert len(data_points) > 0
    # One of them should be "Apple"
    assert any(d.value == "Apple" for d in data_points)
    db.close()
