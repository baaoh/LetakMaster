import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, SourceFile, SourceData, PSDFile, LayerMapping
from app.bridge_service import BridgeService

# Test Database setup
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

def test_verify_psd_logic(db):
    # 1. Setup DB data
    sf = SourceFile(filename="src.xlsx", path="src.xlsx")
    db.add(sf)
    db.commit()
    
    sd1 = SourceData(source_file_id=sf.id, row_index=7, column_name="Product", value="Apple")
    sd2 = SourceData(source_file_id=sf.id, row_index=7, column_name="Price", value="1.99")
    db.add_all([sd1, sd2])
    db.commit()
    
    psd = PSDFile(filename="out.psd", path="out.psd")
    db.add(psd)
    db.commit()
    
    lm1 = LayerMapping(source_data_id=sd1.id, psd_file_id=psd.id, layer_name="name_layer")
    lm2 = LayerMapping(source_data_id=sd2.id, psd_file_id=psd.id, layer_name="price_layer")
    db.add_all([lm1, lm2])
    db.commit()
    
    # 2. Mock PSD content (one matches, one differs)
    mock_psd_content = {
        "name_layer": "Apple",      # Match
        "price_layer": "2.50"       # Mismatch (DB has 1.99)
    }
    
    with patch('app.psd_service.PSDService.read_layers', return_value=mock_psd_content):
        service = BridgeService(db)
        report = service.verify_psd(psd.id)
        
        assert report["status"] == "mismatch"
        assert len(report["discrepancies"]) == 1
        assert report["discrepancies"][0]["layer"] == "price_layer"
        assert report["discrepancies"][0]["db_value"] == "1.99"
        assert report["discrepancies"][0]["psd_value"] == "2.50"
