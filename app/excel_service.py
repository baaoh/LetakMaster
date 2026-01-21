import xlwings as xw
import os
import json
import hashlib

class ExcelService:
    def _rgb_to_hex(self, rgb_tuple):
        if not rgb_tuple or not isinstance(rgb_tuple, (tuple, list)):
            return None
        return '#%02x%02x%02x' % (int(rgb_tuple[0]), int(rgb_tuple[1]), int(rgb_tuple[2]))

    def parse_file(self, file_path: str, header_row: int = 6, sheet_name: str = None, password: str = None):
        """
        Parses an Excel file starting from header_row.
        Uses bulk reading for speed and extracts formatting.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        results = []
        
        app = xw.App(visible=False)
        try:
            if password:
                wb = app.books.open(file_path, password=password)
            else:
                wb = app.books.open(file_path)
            
            if sheet_name:
                try:
                    sheet = wb.sheets[sheet_name]
                except Exception:
                    # Fallback or error? For MVP, assume index 0 if not found, or raise.
                    # Raising is better for "Watch specific sheet" logic.
                    raise ValueError(f"Sheet '{sheet_name}' not found")
            else:
                sheet = wb.sheets[0]
            
            # 1. Get headers
            header_range = sheet.range(f"{header_row}:{header_row}")
            headers_raw = header_range.value
            headers = [h for h in headers_raw if h is not None]
            num_cols = len(headers)
            print(f"DEBUG: Found {num_cols} headers at row {header_row}: {headers}")
            
            # 2. Find last row
            last_row = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row
            print(f"DEBUG: Last row detected: {last_row}")
            
            if last_row <= header_row:
                print("DEBUG: No data rows found.")
                return []

            # 3. Read data and formatting in bulk if possible, 
            # but xlwings 'color' property on range isn't a simple list of lists.
            # We'll iterate rows to keep it manageable but still use range per row.
            
            for r in range(header_row + 1, last_row + 1):
                row_data = {}
                row_range = sheet.range((r, 1), (r, num_cols))
                row_values = row_range.value
                
                for c_idx, value in enumerate(row_values):
                    col_name = headers[c_idx]
                    cell = row_range[c_idx]
                    
                    formatting = {
                        "bold": cell.api.Font.Bold,
                        "color": self._rgb_to_hex(cell.color)
                    }
                    
                    row_data[col_name] = {
                        "value": value,
                        "formatting": formatting
                    }
                results.append(row_data)
                
            wb.close()
        finally:
            app.quit()
            
        return results

    def calculate_hash(self, file_path: str, sheet_name: str = None, password: str = None) -> str:
        """
        Calculates a SHA256 hash of the sheet's data content (values only)
        to quickly detect changes.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        app = xw.App(visible=False)
        try:
            if password:
                wb = app.books.open(file_path, password=password)
            else:
                wb = app.books.open(file_path)
            
            if sheet_name:
                sheet = wb.sheets[sheet_name]
            else:
                sheet = wb.sheets[0]
            
            # Get used range values as list of lists
            used_range = sheet.used_range.value
            
            # Serialize to JSON string to hash it
            # Sort keys to ensure deterministic hashing if it were dicts, 
            # but list of lists is ordered by row/col anyway.
            # Convert to string representation
            data_str = json.dumps(used_range, default=str)
            
            wb.close()
            return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
        finally:
            app.quit()
