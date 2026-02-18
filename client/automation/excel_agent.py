import xlwings as xw
import os
import string
import re
import pythoncom
from typing import List, Dict, Optional

class ExcelAgent:
    """
    High-fidelity Excel Agent.
    Handles data cleaning and traceability.
    """
    def __init__(self, visible=False):
        # Initialize COM for the current thread
        pythoncom.CoInitialize()
        self.app = xw.App(visible=visible, add_book=False)

    def _get_column_letter(self, n):
        res = ""
        while n >= 0:
            res = chr(n % 26 + 65) + res
            n = n // 26 - 1
        return res

    def _clean_number(self, val):
        """Converts strings like '999,0' or '1.200,50' to float."""
        if val is None: return 0.0
        if isinstance(val, (int, float)): return float(val)
        
        # Remove whitespace and replace European comma with dot
        s = str(val).strip().replace(" ", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return 0.0

    def _clean_int(self, val):
        """Safely converts to int, handling '1.0' or '999,0' strings."""
        f = self._clean_number(val)
        return int(f)

    def list_sheets(self, file_path: str, password: Optional[str] = None) -> List[str]:
        """Utility to get sheet names for the UI dropdown."""
        wb = None
        try:
            wb = self.app.books.open(file_path, read_only=True, password=password)
            names = [s.name for s in wb.sheets]
            return names
        finally:
            if wb: wb.close()

    def read_master_data(self, file_path: str, sheet_name: str, password: Optional[str] = None) -> List[Dict]:
        wb = None
        try:
            print(f"Opening Excel: {file_path}")
            wb = self.app.books.open(file_path, read_only=True, password=password)
            
            # Capture metadata (Last Author)
            last_author = "System"
            try:
                # Use a more resilient way to access COM properties
                prop = wb.api.BuiltinDocumentProperties("Last Author")
                if prop and prop.Value:
                    last_author = str(prop.Value).strip()
            except Exception as meta_err:
                print(f"Metadata Warning: {meta_err}")
                last_author = "Unknown Designer"

            sheet = wb.sheets[sheet_name]
            
            headers_raw = sheet.range("A6:AY6").value
            headers = {self._get_column_letter(i): (str(h) if h else f"Col_{self._get_column_letter(i)}") for i, h in enumerate(headers_raw)}

            last_row = sheet.range('V' + str(sheet.cells.last_cell.row)).end('up').row
            if last_row < 7: return []

            raw_values = sheet.range(f"A7:AY{last_row}").value
            
            # Add metadata to the return data
            parsed = self._parse_rows_with_headers(raw_values, headers)
            for row in parsed:
                row["excel_author"] = last_author
            
            return parsed
        except Exception as e:
            print(f"Excel Read Error: {e}")
            raise e
        finally:
            if wb: wb.close()

    def _parse_rows_with_headers(self, raw_rows: List[List], headers: Dict[str, str]) -> List[Dict]:
        parsed = []
        for i, row in enumerate(raw_rows):
            if not row[21]: continue
            
            row_data = {
                "page": self._clean_int(row[0]),
                "product_name": str(row[21]).strip(),
                "raw_index": i + 7,
                "full_data": {}
            }
            
            for col_idx, value in enumerate(row):
                col_letter = self._get_column_letter(col_idx)
                row_data["full_data"][col_letter] = {
                    "header": headers[col_letter],
                    "value": value
                }
            
            parsed.append(row_data)
        return parsed

    def quit(self):
        try:
            self.app.quit()
        finally:
            pythoncom.CoUninitialize()
