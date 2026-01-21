import xlwings as xw
import os
import json
import hashlib
import msoffcrypto
import tempfile

class ExcelService:
    def _rgb_to_hex(self, rgb_tuple):
        if not rgb_tuple or not isinstance(rgb_tuple, (tuple, list)):
            return None
        return '#%02x%02x%02x' % (int(rgb_tuple[0]), int(rgb_tuple[1]), int(rgb_tuple[2]))

    def _unlock_file(self, file_path, password):
        """
        Decrypts the file to a temporary location.
        Returns the path to the decrypted temporary file.
        The caller is responsible for deleting it.
        """
        if not password:
            return file_path, False

        with open(file_path, "rb") as f:
            office_file = msoffcrypto.OfficeFile(f)
            office_file.load_key(password=password)
            
            # Create a temp file with same extension
            ext = os.path.splitext(file_path)[1]
            fd, temp_path = tempfile.mkstemp(suffix=ext)
            os.close(fd) # Close file descriptor, we just needed the name
            
            with open(temp_path, "wb") as f_dec:
                office_file.decrypt(f_dec)
                
        return temp_path, True

    def parse_file(self, file_path: str, header_row: int = 6, sheet_name: str = None, password: str = None):
        """
        Parses an Excel file starting from header_row.
        Uses bulk reading for speed and extracts formatting.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        results = []
        is_temp = False
        actual_path = file_path
        
        try:
            actual_path, is_temp = self._unlock_file(file_path, password)
        except Exception as e:
            print(f"Decryption failed: {e}")
            # If decryption fails (maybe it wasn't encrypted?), try original
            actual_path = file_path

        app = xw.App(visible=False)
        try:
            # Open without password, as we decrypted it
            wb = app.books.open(actual_path)
            
            if sheet_name:
                try:
                    sheet = wb.sheets[sheet_name]
                except Exception:
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
                # Don't return yet, ensure cleanup
            else:
                # 3. Read data
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
            if is_temp and os.path.exists(actual_path):
                try:
                    os.remove(actual_path)
                except:
                    pass
            
        return results

    def calculate_hash(self, file_path: str, sheet_name: str = None, password: str = None) -> str:
        """
        Calculates a SHA256 hash of the sheet's data content (values only).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        is_temp = False
        actual_path = file_path
        
        try:
            actual_path, is_temp = self._unlock_file(file_path, password)
        except Exception as e:
            print(f"Decryption failed: {e}")
            actual_path = file_path

        app = xw.App(visible=False)
        try:
            wb = app.books.open(actual_path)
            if sheet_name:
                sheet = wb.sheets[sheet_name]
            else:
                sheet = wb.sheets[0]
            
            # Get used range values
            used_range = sheet.used_range.value
            data_str = json.dumps(used_range, default=str)
            
            wb.close()
            return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
        finally:
            app.quit()
            if is_temp and os.path.exists(actual_path):
                try:
                    os.remove(actual_path)
                except:
                    pass
