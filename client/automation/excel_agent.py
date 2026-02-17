import xlwings as xw
import os
from typing import List, Dict, Optional
from core.utils.config import settings

class ExcelAgent:
    """
    The 'Hands' of the Designer Client.
    Runs locally on Windows via Embedded Python to drive Excel COM.
    """
    def __init__(self, visible=False):
        self.app = xw.App(visible=visible, add_book=False)

    def read_master_data(self, file_path: str, sheet_name: str) -> List[Dict]:
        """
        Reads the raw product data from the Master Excel.
        """
        try:
            wb = self.app.books.open(file_path, read_only=True)
            sheet = wb.sheets[sheet_name]
            
            # Use same logic as before (Col A to AY)
            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
            data = sheet.range(f"A7:AY{last_row}").value
            
            wb.close()
            return data
        except Exception as e:
            print(f"Excel Read Error: {e}")
            raise e

    def write_enrichment(self, file_path: str, sheet_name: str, enrichment_data: List[List]):
        """
        Writes calculated layout data (PSD Groups, etc) back to columns AL-AY.
        """
        try:
            wb = self.app.books.open(file_path)
            sheet = wb.sheets[sheet_name]
            
            # Start writing at AL7
            sheet.range("AL7").value = enrichment_data
            
            wb.save()
            wb.close()
            return True
        except Exception as e:
            print(f"Excel Write Error: {e}")
            raise e

    def quit(self):
        self.app.quit()
