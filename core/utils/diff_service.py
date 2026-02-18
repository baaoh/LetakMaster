from typing import List, Dict, Optional, Tuple
import json

class DiffService:
    """
    The engine for 'Git-Style' Sync.
    Now updated to handle High-Fidelity 'full_data' structures.
    """
    def __init__(self, key_field: str = "product_name"):
        self.key_field = key_field

    def calculate_diff(self, old_data: List[Dict], new_data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        diff_records = []
        
        old_map = {str(r.get(self.key_field)): r for r in old_data}
        new_map = {str(r.get(self.key_field)): r for r in new_data}
        
        all_keys = set(old_map.keys()) | set(new_map.keys())
        added, removed, modified = 0, 0, 0
        
        for key in all_keys:
            old_row = old_map.get(key)
            new_row = new_map.get(key)
            
            if not old_row:
                added += 1
                diff_records.append({
                    "product_name": key,
                    "field_name": "row",
                    "old_value": None,
                    "new_value": "Added",
                    "change_type": "Info"
                })
            elif not new_row:
                removed += 1
                diff_records.append({
                    "product_name": key,
                    "field_name": "row",
                    "old_value": "Existing",
                    "new_value": None,
                    "change_type": "Info"
                })
            else:
                row_changes = self._compare_rows(key, old_row, new_row)
                if row_changes:
                    modified += 1
                    diff_records.extend(row_changes)
                    
        summary = f"Added: {added}, Removed: {removed}, Modified: {modified}"
        return diff_records, summary

    def _compare_rows(self, product_name: str, old_row: Dict, new_row: Dict) -> List[Dict]:
        changes = []
        
        # Mapping our friendly names to Excel Column Letters
        # price = AC, hero = AK, weight = AA, EAN = W
        critical_fields = {
            "AC": "Price",
            "AK": "Hero Status",
            "W": "EAN",
            "V": "Product Name"
        }
        
        old_full = old_row.get("full_data", {})
        new_full = new_row.get("full_data", {})
        
        for col_letter, friendly_name in critical_fields.items():
            # Get values from inside the 'full_data' -> col -> 'value' structure
            v_old = old_full.get(col_letter, {}).get("value")
            v_new = new_full.get(col_letter, {}).get("value")
            
            if str(v_old) != str(v_new):
                severity = "Critical" if friendly_name in ["Price", "Hero Status"] else "Info"
                changes.append({
                    "product_name": product_name,
                    "field_name": friendly_name,
                    "old_value": str(v_old) if v_old is not None else "",
                    "new_value": str(v_new) if v_new is not None else "",
                    "change_type": severity
                })
        return changes
