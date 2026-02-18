import os
import sys

# Force project root into path for imports
sys.path.append(os.getcwd())

from core.database import SessionLocal
from core.models.schema import Project
from sqlalchemy import select

def init_project():
    print("Connecting to shared database...")
    db = SessionLocal()
    
    # Check if Project 1 already exists using modern 2.0 syntax
    existing = db.get(Project, 1)
    if existing:
        print(f"Project 1 ('{existing.name}') already exists. skipping.")
        return

    print("Creating Project 1: Weekly Flyer...")
    new_project = Project(
        id=1,
        name="Weekly Flyer 2026",
        # Path on the NAS relative to the root
        master_excel_path="Master_Data/Master_2026.xlsx",
        network_root_path="Campaigns/Weekly_2026",
        is_active=True
    )
    
    db.add(new_project)
    db.commit()
    print("Successfully initialized Project 1 in the shared database!")
    db.close()

if __name__ == "__main__":
    init_project()
