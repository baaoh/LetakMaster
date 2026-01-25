import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db, engine as prod_engine
from unittest.mock import patch, MagicMock

import app.main as app_module
from app.database import Base, engine, get_db

@pytest.fixture
def client():
    # Ensure tables exist on the engine the app is using
    Base.metadata.create_all(bind=engine)
    with TestClient(app_module.app) as c:
        yield c
    # Clean up tables after test
    Base.metadata.drop_all(bind=engine)

@pytest.mark.anyio
async def test_trigger_generate_task(client):
    # Register a dummy PSD first
    reg_resp = client.post("/psd/register?filename=test.psd&path=test.psd")
    psd_id = reg_resp.json()["id"]
    
    with patch('app.tkq.generate_psd_task.kiq') as mock_kiq:
        mock_task = MagicMock()
        mock_task.task_id = "test-task-id"
        mock_kiq.return_value = mock_task
        
        response = client.post(f"/psd/{psd_id}/generate")
        assert response.status_code == 200
        assert response.json()["task_id"] == "test-task-id"
        mock_kiq.assert_called_once_with(psd_id)

@pytest.mark.anyio
async def test_trigger_verify_task(client):
    reg_resp = client.post("/psd/register?filename=test.psd&path=test.psd")
    psd_id = reg_resp.json()["id"]
    
    with patch('app.tkq.verify_psd_task.kiq') as mock_kiq:
        mock_task = MagicMock()
        mock_task.task_id = "verify-task-id"
        mock_kiq.return_value = mock_task
        
        response = client.post(f"/psd/{psd_id}/verify")
        assert response.status_code == 200
        assert response.json()["task_id"] == "verify-task-id"
        mock_kiq.assert_called_once_with(psd_id)
