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
            print(f"DEBUG: Attempting to unlock file: {file_path} (Password provided: {bool(password)})")
            actual_path, is_temp = self._unlock_file(file_path, password)
            print(f"DEBUG: Unlock successful. Reading from: {actual_path} (Temp: {is_temp})")
        except Exception as e:
            print(f"DEBUG: Decryption failed: {e}")
            # If decryption fails (maybe it wasn't encrypted?), try original
            actual_path = file_path

        app = xw.App(visible=False)
        try:
            print("DEBUG: Opening workbook with xlwings...")
            # Open without password, as we decrypted it
            wb = app.books.open(actual_path)
            print("DEBUG: Workbook opened.")
            
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
            
            # Preserve indices. Generate default name if missing.
            headers = []
            valid_indices = [] # Track which columns we actually want to read
            
            for idx, h in enumerate(headers_raw):
                if h is not None and str(h).strip():
                    headers.append(str(h).strip())
                    valid_indices.append(idx)
                else:
                    # If header is empty, do we skip data? 
                    # User says "there is no header but there is data".
                    # So we should probably capture it.
                    # Let's generate a placeholder.
                    headers.append(f"Column_{idx+1}")
                    valid_indices.append(idx)

            num_cols = len(headers_raw) # Read all columns up to the end of the used range in that row? 
            # Actually headers_raw comes from range("6:6") which is the WHOLE row (16384 cols). 
            # We need to trim trailing empty headers.
            
            # Refined strategy: Find last used column in header row
            last_col_idx = -1
            for i in range(len(headers_raw) - 1, -1, -1):
                if headers_raw[i] is not None:
                    last_col_idx = i
                    break
            
            # Slice headers to relevant range
            relevant_headers = headers_raw[:last_col_idx+1]
            final_headers = []
            
            for i, h in enumerate(relevant_headers):
                if h is None:
                    final_headers.append(f"Column_{i+1}")
                else:
                    final_headers.append(str(h))
            
            num_read_cols = len(final_headers)
            print(f"DEBUG: Found {num_read_cols} headers (trimmed): {final_headers}")
            
            # 2. Find last row
            last_row = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row
            print(f"DEBUG: Last row detected: {last_row}")
            
            if last_row <= header_row:
                print("DEBUG: No data rows found.")
            else:
                # 3. Bulk Read Data (Values & Colors)
                # Define the full data range
                data_range = sheet.range((header_row + 1, 1), (last_row, num_read_cols))
                
                print("DEBUG: Bulk reading values...")
                all_values = data_range.value
                
                print("DEBUG: Bulk reading colors...")
                all_colors = data_range.color
                
                # Normalize all_values to list of lists if single row
                if not isinstance(all_values[0], (list, tuple)):
                    all_values = [all_values]
                    all_colors = [all_colors]
                
                print(f"DEBUG: Processing {len(all_values)} rows in memory...")

                for r_idx, row_vals in enumerate(all_values):
                    row_data = {}
                    
                    # Ensure row_vals is iterable (if single col, it might be scalar? xlwings usually handles this with options(ndim=2) but we used default)
                    # If num_read_cols == 1, row_vals might be a scalar value per row? 
                    # Let's ensure safety.
                    current_row_vals = row_vals if isinstance(row_vals, (list, tuple)) else [row_vals]
                    
                    for c_idx, col_name in enumerate(final_headers):
                        if c_idx >= len(current_row_vals):
                            break
                            
                        val = current_row_vals[c_idx]
                        
                        # Color extraction
                        # all_colors structure matches all_values
                        # If single col/row, xlwings might flatten. 
                        # Assuming 2D consistency for now, but adding safety.
                        bg_color = None
                        try:
                            if all_colors:
                                # Access safely
                                if r_idx < len(all_colors):
                                    row_colors = all_colors[r_idx]
                                    if isinstance(row_colors, (list, tuple)) and c_idx < len(row_colors):
                                        bg_color = self._rgb_to_hex(row_colors[c_idx])
                                    elif not isinstance(row_colors, (list, tuple)) and c_idx == 0:
                                         # Single column case, row_colors might be the tuple directly
                                         bg_color = self._rgb_to_hex(row_colors)
                        except Exception:
                            pass

                        # NOTE: borders and bold removed for performance (requires slow cell-by-cell API calls)
                        formatting = {
                            "bold": False,
                            "color": bg_color,
                            "border": False
                        }
                        
                        row_data[col_name] = {
                            "value": val,
                            "formatting": formatting
                        }
                    results.append(row_data)
                print("DEBUG: Processing complete.")
                
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
            print(f"DEBUG: HASH - Attempting to unlock file: {file_path}")
            actual_path, is_temp = self._unlock_file(file_path, password)
            print(f"DEBUG: HASH - Unlock successful.")
        except Exception as e:
            print(f"DEBUG: HASH - Decryption failed: {e}")
            actual_path = file_path

        app = xw.App(visible=False)
        try:
            print("DEBUG: HASH - Opening workbook...")
            wb = app.books.open(actual_path)
            print("DEBUG: HASH - Workbook opened.")
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

    def get_file_metadata(self, file_path: str, password: str = None):
        """
        Extracts metadata (Last Author) from the Excel file.
        """
        if not os.path.exists(file_path):
            return {}

        is_temp = False
        actual_path = file_path
        
        try:
            actual_path, is_temp = self._unlock_file(file_path, password)
        except Exception:
            actual_path = file_path

        app = xw.App(visible=False)
        metadata = {}
        try:
            if password:
                wb = app.books.open(actual_path, password=password)
            else:
                wb = app.books.open(actual_path)
            
            # Access Builtin properties
            # This is specific to the COM object (Windows Excel)
            try:
                # 7 corresponds to "Last Author" / "Last Saved By" in MsoDocProperties
                # Or access by name if supported by the wrapper
                # xlwings book.api returns the native object
                doc_props = wb.api.BuiltinDocumentProperties
                last_author = doc_props("Last Author").Value
                metadata["last_modified_by"] = str(last_author)
            except Exception as e:
                print(f"DEBUG: Could not read metadata: {e}")
                metadata["last_modified_by"] = None
            
            wb.close()
        except Exception as e:
            print(f"DEBUG: Metadata fetch error: {e}")
        finally:
            app.quit()
            if is_temp and os.path.exists(actual_path):
                try:
                    os.remove(actual_path)
                except:
                    pass
        
        return metadata

    def get_sheet_names(self, file_path: str, password: str = None):
        """
        Returns a list of sheet names from the Excel file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        is_temp = False
        actual_path = file_path
        
        try:
            actual_path, is_temp = self._unlock_file(file_path, password)
        except Exception:
            actual_path = file_path

        app = xw.App(visible=False)
        sheet_names = []
        try:
            if password:
                wb = app.books.open(actual_path, password=password)
            else:
                wb = app.books.open(actual_path)
            
            sheet_names = [sheet.name for sheet in wb.sheets]
            wb.close()
        finally:
            app.quit()
            if is_temp and os.path.exists(actual_path):
                try:
                    os.remove(actual_path)
                except:
                    pass
        
        return sheet_names

    def open_file_in_gui(self, file_path: str, password: str = None):
        """
        Opens the file in the visible Excel application.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Use xlwings to open (visible=True by default for main app, 
        # but our service usually creates visible=False apps.
        # We want to use the USER'S active Excel or start one.)
        
        # xw.Book(file_path) connects to active or opens.
        # But we want to handle password.
        
        try:
            app = xw.App(visible=True, add_book=False)
            app.activate(steal_focus=True)
            
            if password:
                wb = app.books.open(file_path, password=password)
            else:
                wb = app.books.open(file_path)
                
            wb.activate()
            return True
        except Exception as e:
            print(f"Failed to open Excel GUI: {e}")
            # Fallback to OS shell (user will be prompted for password)
            os.startfile(file_path)
            return False
