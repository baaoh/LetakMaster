import os
import shutil
import requests
from datetime import datetime
from typing import List, Dict, Optional
from core.utils.config import settings
from core.utils.path_manager import PathManager
from client.automation.excel_agent import ExcelAgent

class SyncManager:
    """
    Orchestrates the 'Commit' process from a Designer PC to the Synology Hub.
    """
    def __init__(self):
        self.paths = PathManager()
        self.excel = ExcelAgent()

    def perform_sync(self, project_id: int, excel_path: str, sheet_name: str = "DATA", password: Optional[str] = None) -> Dict:
        """
        1. Reads local Excel using high-fidelity column mapping.
        2. Copies file to NAS Archives.
        3. Pushes data to Synology Hub.
        """
        try:
            # 1. Read Data (Using the refined ExcelAgent)
            print(f"Reading Master Excel: {excel_path} (Sheet: {sheet_name})")
            raw_parsed_data = self.excel.read_master_data(excel_path, sheet_name, password=password)
            
            if not raw_parsed_data:
                raise Exception(f"No product data found in sheet '{sheet_name}'")

            # Capture Excel Author from the first row (populated by ExcelAgent)
            excel_author = raw_parsed_data[0].get("excel_author", "Unknown")

            # 2. Create NAS Archive
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"{timestamp}_{settings.user_id}.xlsx"
            rel_archive_dir = f"Archives/Project_{project_id}"
            
            # Ensure the directory exists on the NAS (via L:/)
            abs_archive_dir = self.paths.to_full_path(rel_archive_dir)
            os.makedirs(abs_archive_dir, exist_ok=True)
            
            abs_archive_path = os.path.join(abs_archive_dir, filename)
            rel_archive_path = f"{rel_archive_dir}/{filename}"
            
            print(f"Archiving to NAS: {abs_archive_path}")
            shutil.copy2(excel_path, abs_archive_path)

            # 3. Push to Hub API (The Synology Hub)
            payload = {
                "project_id": project_id,
                "user_id": settings.user_id,
                "sheet_name": sheet_name,
                "excel_author": excel_author,
                "new_data": raw_parsed_data,
                "archive_path": rel_archive_path
            }
            
            print(f"Pushing to Hub: {settings.hub_url}/sync/push")
            response = requests.post(f"{settings.hub_url}/sync/push", json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Hub Sync Failed: {response.text}")

        finally:
            # Always close the Excel app window, even if it fails
            self.excel.quit()
