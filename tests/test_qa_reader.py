import os
import sys
import pytest

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.qa.psd_reader import PSDReader

# We need a dummy PSD for this test.
# Since we can't easily create a valid binary PSD from scratch in python without psd-tools writing (which is limited),
# We will mock the PSDImage.open behavior or skip if no file exists.

def test_psd_reader_structure(tmp_path):
    # Setup
    out_dir = tmp_path / "scans"
    prev_dir = tmp_path / "previews"
    reader = PSDReader(str(out_dir), str(prev_dir))
    
    # Assert Dirs created
    assert os.path.exists(str(out_dir))
    assert os.path.exists(str(prev_dir))
    
    # We can't really test process_file without a real PSD file.
    # But we can verify the class loads and methods exist.
    assert hasattr(reader, 'process_file')
