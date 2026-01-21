import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch
from app.psd_service import PSDService

def test_psd_service_read_layers_mock():
    # Mocking psd-tools PSDImage
    with patch('psd_tools.PSDImage.open') as mock_open:
        mock_psd = MagicMock()
        mock_open.return_value = mock_psd
        
        # Mocking layer structure
        layer1 = MagicMock()
        layer1.name = "product_name"
        layer1.kind = "type" # psd-tools kind for text layers
        layer1.text = "Old Product"
        layer1.is_group.return_value = False
        
        layer2 = MagicMock()
        layer2.name = "price"
        layer2.kind = "type"
        layer2.text = "0.00"
        layer2.is_group.return_value = False
        
        mock_psd.descendants.return_value = [layer1, layer2]
        
        service = PSDService()
        layers = service.read_layers("dummy.psd")
        
        assert "product_name" in layers
        assert layers["product_name"] == "Old Product"
        assert layers["price"] == "0.00"

def test_psd_service_update_layers_mock():
    with patch('psd_tools.PSDImage.open') as mock_open:
        mock_psd = MagicMock()
        mock_open.return_value = mock_psd
        
        layer1 = MagicMock()
        layer1.name = "product_name"
        layer1.kind = "type"
        layer1.text = "Old Product"
        layer1.is_group.return_value = False
        
        mock_psd.descendants.return_value = [layer1]
        
        service = PSDService()
        service.update_layers("dummy.psd", {"product_name": "New Awesome Product"}, "output.psd")
        
        assert layer1.text == "New Awesome Product"
        mock_psd.save.assert_called_once_with("output.psd")
