import json
import os
import re
from thefuzz import fuzz

class QAMatcher:
    def __init__(self):
        pass

    def match_page(self, build_plan_path, scan_path):
        """
        Matches a Build Plan (Expected) against a Raw PSD Scan (Actual).
        Returns a dictionary keyed by Group ID (Product_XX) containing matched actual values.
        """
        if not os.path.exists(build_plan_path):
            print(f"Build Plan not found: {build_plan_path}")
            return {}
        
        if not os.path.exists(scan_path):
            print(f"Scan not found: {scan_path}")
            return {}

        with open(build_plan_path, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        
        with open(scan_path, 'r', encoding='utf-8') as f:
            scan = json.load(f)
            
        raw_layers = scan.get("layers", [])
        
        # We need to map: GroupID -> { Attribute -> ActualValue }
        results = {}
        
        for action in plan.get("actions", []):
            group_id = action.get("group")
            expected_data = action.get("data", {})
            expected_vis = action.get("visibility", {})
            
            # Initialize result for this group
            results[group_id] = {
                "layers": {} 
            }
            
            # For each attribute in the plan (nazev_01A, cena_01A, etc.)
            # We want to find the BEST matching layer in the raw scan.
            
            # 1. Collect all attributes we care about for this group
            # We look at keys in 'data' AND 'visibility'
            all_keys = set(expected_data.keys()) | set(expected_vis.keys())
            
            for key in all_keys:
                expected_val = expected_data.get(key, "")
                is_visible_expected = expected_vis.get(key, True) # Default expected visible?
                
                # Logic: Find best layer match for this 'key'
                best_match = None
                best_score = -1
                
                # Heuristic Pre-calculation: Expected suffix from key?
                # e.g. "nazev_01A" -> suffix "01A"
                # This helps matching "nazev_01A copy"
                
                for layer in raw_layers:
                    score = 0
                    
                    # 1. VISIBILITY CHECK
                    # If we expect it to be visible, prefer visible layers heavily
                    # If the layer is hidden, punish score
                    if layer["visible"]:
                        score += 20
                    else:
                        score -= 50 # Strong penalty for hidden layers if we are looking for content
                    
                    # 2. NAME MATCHING (Strongest Signal)
                    # Does the layer name contain the key?
                    # e.g. key="nazev_01a", layer="nazev_01A copy"
                    layer_name = layer["name"].lower()
                    key_lower = key.lower()
                    
                    if key_lower == layer_name:
                        score += 100 # Exact Name Match
                    elif key_lower in layer_name:
                        score += 80 # Partial Name Match
                        
                    # 3. TEXT MATCHING (Confirmation)
                    # If we have expected text, compare it.
                    # But be careful: Price "19" vs "19,90" might be fuzzy.
                    # If expected text is empty, we rely solely on Name.
                    
                    actual_text = layer["text"]
                    if expected_val:
                        text_score = fuzz.ratio(str(expected_val).lower(), actual_text.lower())
                        # Weight text score. If name matches perfectly, text score matters less?
                        # No, if name matches perfectly, we found the layer.
                        # Text mismatch just means content mismatch (which is what we want to report).
                        # So, we use Text Score mainly to disambiguate if Names are ambiguous?
                        # actually, we use Name to FIND the layer, and Text is what we extract.
                        # So we shouldn't use Text similarity to FIND the layer unless Name is missing/bad.
                        pass
                    
                    if score > best_score:
                        best_score = score
                        best_match = layer
                
                # Threshold for a "Match"
                # If best_score is low (e.g. only 20 for visibility), it's probably not the right layer.
                # We need at least some name match?
                if best_score > 40 and best_match:
                    # Record the ACTUAL text and visibility found in the best layer
                    results[group_id]["layers"][key.lower()] = {
                        "text": best_match["text"],
                        "visible": best_match["visible"],
                        "matched_layer": best_match["name"],
                        "bbox": best_match.get("bbox"),
                        "score": best_score
                    }
                else:
                    # No match found for this key
                    results[group_id]["layers"][key.lower()] = {
                        "text": None,
                        "visible": False,
                        "matched_layer": None,
                        "bbox": None
                    }
                    
        return results

