from typing import List, Dict, Optional, Tuple
import json

class DiffService:
    """
    The engine for 'Git-Style' Sync.
    Compares two data snapshots (List of Rows) and returns granular changes.
    """
    def __init__(self, key_field: str = "product_name"):
        self.key_field = key_field

    def calculate_diff(self, old_data: List[Dict], new_data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Calculates changes between two versions of a page's data.
        Returns: (List[DataDiffRecords], SummaryString)
        """
        diff_records = []
        summary_parts = []
        
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
                # Row exists in both, check fields
                row_changes = self._compare_rows(key, old_row, new_row)
                if row_changes:
                    modified += 1
                    diff_records.extend(row_changes)
                    
        summary = f"Added: {added}, Removed: {removed}, Modified: {modified}"
        return diff_records, summary

    def _compare_rows(self, product_name: str, old_row: Dict, new_row: Dict) -> List[Dict]:
        changes = []
        # Key fields to check for changes
        fields_to_check = ["price", "hero", "weight_text", "product_name"]
        
        for field in fields_to_check:
            v_old = old_row.get(field)
            v_new = new_row.get(field)
            
            if v_old != v_new:
                severity = "Critical" if field in ["price", "hero"] else "Info"
                changes.append({
                    "product_name": product_name,
                    "field_name": field,
                    "old_value": str(v_old),
                    "new_value": str(v_new),
                    "change_type": severity
                })
        return changes
