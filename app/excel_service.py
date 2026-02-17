import xlwings as xw
import os
import json
import hashlib
import msoffcrypto
import tempfile
import pandas as pd
import openpyxl

class ExcelService:
    def _rgb_to_hex(self, rgb_tuple):
        if not rgb_tuple or not isinstance(rgb_tuple, (tuple, list)):
            return None
        return '#%02x%02x%02x' % (int(rgb_tuple[0]), int(rgb_tuple[1]), int(rgb_tuple[2]))

    def _deep_clean_excel(self, file_path: str):
        """
        Uses openpyxl to strip ALL named ranges, external links, and table references.
        This fixes the XML corruption issue where copied sheets carry over broken references.
        """
        try:
            print(f"DEBUG: Deep cleaning {file_path} with openpyxl...")
            wb = openpyxl.load_workbook(file_path)
            
            # 1. Clear Global Defined Names
            if hasattr(wb, 'defined_names'):
                wb.defined_names.definedName = []
            
            # 2. Clear Worksheet-specific names and Tables
            for sheet in wb.worksheets:
                # Clear sheet-level defined names if any (though openpyxl usually keeps them in wb.defined_names with localSheetId)
                # But we'll be thorough.
                
                # Clear Tables - often source of "Removed Records" if names clash
                if hasattr(sheet, '_tables'):
                    sheet._tables = []
            
            # 3. Clear External Links (The "Repaired Records: External formula reference" fix)
            if hasattr(wb, '_external_links'):
                wb._external_links = []
            
            # 4. Save changes
            wb.save(file_path)
            wb.close()
            print("DEBUG: Deep clean complete.")
            return True
        except Exception as e:
            print(f"Error during deep clean: {e}")
            return False

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
            # New method: Use Excel's Find method to find the last row with any content
            try:
                # SearchOrder=1 (xlByRows), SearchDirection=2 (xlPrevious)
                last_row = sheet.cells.api.Find("*", SearchOrder=1, SearchDirection=2).Row
            except Exception:
                # Fallback to used_range if Find fails (e.g. empty sheet)
                try:
                    last_row = sheet.used_range.last_cell.row
                except:
                    last_row = header_row # Assume only header
                
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
                    current_row_vals = row_vals if isinstance(row_vals, (list, tuple)) else [row_vals]
                    
                    for c_idx, col_name in enumerate(final_headers):
                        if c_idx >= len(current_row_vals):
                            break
                            
                        val = current_row_vals[c_idx]
                        
                        # Color extraction
                        bg_color = None
                        try:
                            if all_colors:
                                if r_idx < len(all_colors):
                                    row_colors = all_colors[r_idx]
                                    if isinstance(row_colors, (list, tuple)) and c_idx < len(row_colors):
                                        bg_color = self._rgb_to_hex(row_colors[c_idx])
                                    elif not isinstance(row_colors, (list, tuple)) and c_idx == 0:
                                         bg_color = self._rgb_to_hex(row_colors)
                        except Exception:
                            pass

                        # NOTE: borders and bold removed for performance
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
            
            try:
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

    def open_file_in_gui(self, file_path: str, password: str = None):
        """
        Opens the file in the visible Excel application.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            app = xw.App(visible=True, add_book=False)
            app.activate(steal_focus=True)
            
            if password:
                wb = app.books.open(file_path, password=password, read_only=False)
            else:
                wb = app.books.open(file_path, read_only=False)
                
            wb.activate()
            return True
        except Exception as e:
            print(f"Failed to open Excel GUI: {e}")
            os.startfile(file_path)
            return False

    def generate_excel_from_data(self, data: list, output_path: str):
        """
        Generates an Excel file from the state data (list of dicts).
        """
        if not data:
            df = pd.DataFrame()
        else:
            # Data is List[Dict[ColName, {value: ..., formatting: ...}]]
            # We need to flatten it for DataFrame
            flat_data = []
            for row in data:
                flat_row = {}
                for col, cell in row.items():
                    flat_row[col] = cell.get('value')
                flat_data.append(flat_row)
            
            df = pd.DataFrame(flat_data)
            
        # Write to Excel
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            df.to_excel(output_path, index=False)
            return True
        except Exception as e:
            print(f"Failed to write Excel: {e}")
            return False

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

    def archive_sheet(self, source_path, sheet_name, dest_path, password=None):
        """
        Copies specific sheet to a new workbook using xlwings (COM).
        Preserves all formatting.
        """
        if not os.path.exists(source_path):
            return False

        is_temp = False
        actual_path = source_path
        
        try:
            actual_path, is_temp = self._unlock_file(source_path, password)
        except Exception:
            actual_path = source_path

        app = xw.App(visible=False)
        try:
            if password:
                wb_src = app.books.open(actual_path, password=password)
            else:
                wb_src = app.books.open(actual_path)
            
            # Create new workbook
            wb_dest = app.books.add()
            
            # Identify source sheet
            if sheet_name:
                try:
                    sht = wb_src.sheets[sheet_name]
                except:
                    sht = wb_src.sheets[0]
            else:
                sht = wb_src.sheets[0]
            
            # Copy sheet to new workbook
            sht.copy(before=wb_dest.sheets[0])
            
            # Cleanup: Delete the default blank sheet(s) in dest
            # We copied BEFORE the first sheet, so our sheet is index 0.
            # Delete all others.
            for s in wb_dest.sheets:
                if s.name != sht.name:
                    try:
                        s.delete()
                    except:
                        pass
            
            # --- CLEANUP NAMED RANGES ---
            # Drastic measure: Delete ALL names to prevent corruption from broken refs.
            # This fixes "Removed Records: Named range from /xl/workbook.xml part" errors.
            try:
                # 1. Delete Sheet-level names
                for s in wb_dest.sheets:
                    for name in s.names:
                        try: name.delete()
                        except: pass
                
                # 2. Delete Workbook-level names
                # Note: Iterating and deleting can be tricky if the collection changes.
                # Reverse iteration or 'while count > 0' might be safer, but xlwings usually handles it.
                # We'll try standard iteration.
                for name in wb_dest.names:
                    try: name.delete()
                    except: pass
            except Exception as e:
                print(f"Warning: Failed to cleanup named ranges: {e}")

            # Save
            wb_dest.save(dest_path)
            wb_dest.close()
            wb_src.close()
            
            # Post-Save: Deep Clean with openpyxl
            self._deep_clean_excel(dest_path)
            
            return True
        except Exception as e:
            print(f"Archive failed: {e}")
            return False
        finally:
            app.quit()
            if is_temp and os.path.exists(actual_path):
                try:
                    os.remove(actual_path)
                except:
                    pass

    def open_as_new_book(self, source_path):
        """
        Opens the content of source_path in a NEW unsaved workbook.
        This prevents file clutter and acts like a Template.
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"File not found: {source_path}")

        app = xw.App(visible=True, add_book=False)
        # We need the app to be visible for the new book, 
        # but we can hide the source book processing if we want.
        # However, since we are using the visible app instance for the result,
        # the user might see a flicker. This is acceptable.
        
        try:
            # 1. Open Source (Read-onlyish)
            wb_src = app.books.open(source_path)
            
            # 2. Create New Book
            wb_new = app.books.add()
            
            # 3. Copy first sheet
            # We assume archive has 1 sheet.
            wb_src.sheets[0].copy(before=wb_new.sheets[0])
            
            # 4. Clean up new book (remove default blank sheet)
            # The copied sheet is now index 0.
            if len(wb_new.sheets) > 1:
                 wb_new.sheets[1].delete()
            
            # 5. Activate new book
            wb_new.activate()
            
            # 6. Close source without saving
            wb_src.close()
            
            # Return success
            return True
        except Exception as e:
            print(f"Failed to open as new book: {e}")
            raise e

    def inject_vba_trigger(self, file_path: str):
        """
        Injects the Workbook_Open trigger from scripts/VBA_TRIGGER.txt into the file.
        Note: This converts the file to .xlsm and requires 'Trust access to VBA project' to be enabled.
        """
        vba_file = os.path.join(os.getcwd(), "scripts", "VBA_TRIGGER.txt")
        if not os.path.exists(vba_file):
            print("VBA Trigger script not found.")
            return file_path
            
        with open(vba_file, "r", encoding="utf-8") as f:
            vba_code = f.read()

        app = xw.App(visible=False)
        try:
            wb = app.books.open(file_path)
            try:
                # Access the VBProject
                # This WILL fail if the user hasn't enabled 'Trust access to the VBA project object model'
                comp = wb.api.VBProject.VBComponents("ThisWorkbook")
                comp.CodeModule.AddFromString(vba_code)
                print("VBA Trigger injected successfully.")
            except Exception as e:
                print(f"VBA Injection failed (likely 'Trust Access' not enabled): {e}")
                wb.close()
                return file_path

            # Save as XLSM
            base_path = os.path.splitext(file_path)[0]
            xlsm_path = base_path + ".xlsm"
            
            # 52 = xlOpenXMLWorkbookMacroEnabled
            wb.api.SaveAs(xlsm_path, 52)
            wb.close()
            
            # Remove original XLSX if different
            if xlsm_path != file_path and os.path.exists(file_path):
                try: os.remove(file_path)
                except: pass
                
            return xlsm_path
        except Exception as e:
            print(f"Failed to inject VBA: {e}")
            return file_path
        finally:
            app.quit()