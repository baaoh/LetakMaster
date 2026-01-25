import os

def test_project_structure():
    """Verify that key project directories exist."""
    required_dirs = ['app', 'scripts']
    for directory in required_dirs:
        assert os.path.isdir(directory), f"Directory '{directory}' is missing."

def test_requirements_file():
    """Verify that requirements.txt exists and contains key dependencies."""
    assert os.path.isfile('requirements.txt'), "requirements.txt is missing."
    
    required_packages = [
        'fastapi', 
        'sqlalchemy', 
        'xlwings', 
        'psd-tools', 
        'taskiq'
    ]
    
    with open('requirements.txt', 'r') as f:
        content = f.read().lower()
        for package in required_packages:
            assert package in content, f"Package '{package}' is missing from requirements.txt"
