import xlwings as xw
import os
import shutil
import msoffcrypto
import tempfile
import openpyxl
import pythoncom
from typing import Optional
from core.utils.path_manager import PathManager

class WorkspaceManager:
    """Handles collaborative Excel workspace management."""
    def __init__(self):
        self.paths = PathManager()

    def _unlock_file(self, file_path, password):
        if not password: return file_path, False
        try:
            with open(file_path, "rb") as f:
                office_file = msoffcrypto.OfficeFile(f)
                office_file.load_key(password=password)
                ext = os.path.splitext(file_path)[1]
                fd, temp_path = tempfile.mkstemp(suffix=ext); os.close(fd)
                with open(temp_path, "wb") as f_dec: office_file.decrypt(f_dec)
            return temp_path, True
        except: return file_path, False

    def _deep_clean_excel(self, file_path: str):
        try:
            wb = openpyxl.load_workbook(file_path)
            if hasattr(wb, '_external_links'): wb._external_links = []
            if hasattr(wb, 'defined_names'): wb.defined_names.definedName = []
            for sheet in wb.worksheets:
                if hasattr(sheet, '_tables'): sheet._tables = []
            wb.save(file_path); wb.close()
            return True
        except: return False

    def open_and_extract(self, file_path: str, sheet_name: Optional[str] = None, password: Optional[str] = None):
        """
        Collaborative Open Logic:
        1. If local workspace for this specific path exists, open it.
        2. If not (e.g. from another user), extract from Hub Archive.
        """
        temp_decrypted = None
        try:
            pythoncom.CoInitialize()
            abs_source = self.paths.to_full_path(file_path)
            
            # Use a unique local name based on the filename to avoid collisions
            ws_dir = os.path.join(os.getcwd(), "workspaces", "active")
            os.makedirs(ws_dir, exist_ok=True)
            
            # Clean filename: Workspace_20260218_Bao.xls
            clean_name = os.path.basename(abs_source)
            target_path = os.path.join(ws_dir, f"Workspace_{clean_name}")

            # 1. Check local existence (Saves time/password)
            if os.path.exists(target_path):
                print(f"DEBUG: Opening existing local copy: {target_path}")
                app = xw.App(visible=True, add_book=False)
                app.display_alerts = False
                app.books.open(target_path, update_links=False)
                return {"status": "success", "message": f"Opened local copy: {os.path.basename(target_path)}"}

            # 2. Extract from Hub (Collaborative Download)
            if not os.path.exists(abs_source):
                return {"status": "error", "message": f"Source file not found on NAS: {abs_source}"}

            print(f"DEBUG: Extracting fresh copy from Hub: {abs_source}")
            temp_decrypted, was_decrypted = self._unlock_file(abs_source, password)

            app = xw.App(visible=False); app.display_alerts = False 
            try:
                wb_src = app.books.open(temp_decrypted, update_links=False)
                sht = wb_src.sheets[sheet_name] if sheet_name and sheet_name in [s.name for s in wb_src.sheets] else wb_src.sheets[0]

                wb_dest = app.books.add()
                sht.copy(before=wb_dest.sheets[0])
                if len(wb_dest.sheets) > 1: wb_dest.sheets[1].delete()
                
                wb_dest.save(target_path); wb_dest.close(); wb_src.close()
            except Exception as e:
                return {"status": "error", "message": f"Extraction failed: {str(e)}. (Is password correct?)"}
            finally:
                app.quit()

            self._deep_clean_excel(target_path)
            
            # 3. Final Open
            final_app = xw.App(visible=True, add_book=False)
            final_app.display_alerts = False
            final_app.books.open(target_path, update_links=False)
            
            return {"status": "success", "message": f"Downloaded and opened state from Hub."}
        
        except Exception as outer_e:
            return {"status": "error", "message": f"System Error: {str(outer_e)}"}
        finally:
            if temp_decrypted and temp_decrypted != abs_source:
                try: os.remove(temp_decrypted)
                except: pass
            pythoncom.CoUninitialize()
