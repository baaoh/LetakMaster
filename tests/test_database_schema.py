import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, SourceFile, SourceData, PSDFile, LayerMapping

# Use in-memory SQLite for testing
DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def session():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_source_file_model(session):
    source_file = SourceFile(filename="products.xlsx", path="/data/products.xlsx")
    session.add(source_file)
    session.commit()
    assert source_file.id is not None
    assert source_file.filename == "products.xlsx"

def test_source_data_model(session):
    source_file = SourceFile(filename="products.xlsx", path="/data/products.xlsx")
    session.add(source_file)
    session.commit()
    
    data = SourceData(
        source_file_id=source_file.id,
        row_index=1,
        column_name="Product Name",
        value="Apple iPhone 15",
        formatting_json='{"bold": true}'
    )
    session.add(data)
    session.commit()
    assert data.id is not None
    assert data.value == "Apple iPhone 15"

def test_psd_file_model(session):
    psd = PSDFile(filename="catalog_page_1.psd", path="/output/catalog_page_1.psd")
    session.add(psd)
    session.commit()
    assert psd.id is not None
    assert psd.filename == "catalog_page_1.psd"

def test_layer_mapping_model(session):
    source_file = SourceFile(filename="products.xlsx", path="/data/products.xlsx")
    session.add(source_file)
    session.commit()
    
    data = SourceData(source_file_id=source_file.id, row_index=1, column_name="Price", value="999")
    session.add(data)
    
    psd = PSDFile(filename="page1.psd", path="/output/page1.psd")
    session.add(psd)
    session.commit()
    
    mapping = LayerMapping(
        source_data_id=data.id,
        psd_file_id=psd.id,
        layer_name="price_layer"
    )
    session.add(mapping)
    session.commit()
    
    assert mapping.id is not None
    assert mapping.layer_name == "price_layer"
    assert mapping.source_data.value == "999"
    assert mapping.psd_file.filename == "page1.psd"
