import os
import sys
sys.path.append(os.getcwd())
import json
import shutil
from app.database import SessionLocal, engine, ProjectState
from app.excel_service import ExcelService

# Force UTF-8
sys.stdout.reconfigure(encoding='utf-8')

session = SessionLocal()
state = session.query(ProjectState).get(5)

print(f"State 5 found: {bool(state)}")
if state:
    print(f"Archive Path: {state.archive_path}")
    if state.archive_path:
        print(f"Archive Exists: {os.path.exists(state.archive_path)}")

    target_path = os.path.abspath(os.path.join("workspaces", "state_5", "Workspace_State_5.xlsx"))
    print(f"Target Path: {target_path}")
    
    service = ExcelService()
    
    print("Attempting Generation...")
    try:
        data = json.loads(state.data_snapshot_json)
        print(f"Data Rows: {len(data)}")
        success = service.generate_excel_from_data(data, target_path)
        print(f"Generation Success: {success}")
    except Exception as e:
        print(f"Generation Error: {e}")
        import traceback
        traceback.print_exc()

session.close()
