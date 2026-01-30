from psd_tools import PSDImage
from PIL import Image
import os
import json
import re

class PSDReader:
    def __init__(self, output_dir, preview_dir):
        self.output_dir = output_dir
        self.preview_dir = preview_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        if not os.path.exists(preview_dir):
            os.makedirs(preview_dir)

    def process_file(self, file_path):
        filename = os.path.basename(file_path)
        print(f"Processing PSD: {filename}")
        
        try:
            psd = PSDImage.open(file_path)
        except Exception as e:
            print(f"Error opening {filename}: {e}")
            return None

        # 1. Generate Preview (1600px width)
        page_name = os.path.splitext(filename)[0]
        preview_path = os.path.join(self.preview_dir, f"{page_name}.png")
        
        # Render composite
        if not os.path.exists(preview_path):
            try:
                image = psd.composite()
                if image:
                    width, height = image.size
                    if width > 1600:
                        ratio = 1600 / width
                        new_height = int(height * ratio)
                        image = image.resize((1600, new_height), Image.Resampling.LANCZOS)
                    image.save(preview_path, "PNG")
                    print(f"Preview saved: {preview_path}")
            except Exception as e:
                print(f"Preview generation failed: {e}")
        else:
            print(f"Preview already exists: {preview_path}")

        # 2. Extract Data & Coordinates
        extracted_data = {
            "page_name": page_name,
            "groups": {}
        }

        print(f"--- Scanning Layers for {filename} ---")

        # Recursive traversal
        def traverse(layers, depth=0):
            for layer in layers:
                if layer.is_group():
                    name = layer.name.strip()
                    # Debug log top-level groups
                    if depth < 2:
                        print(f"  {'  '*depth}[GRP] {name}")

                    # Check for Product Groups
                    # Match: Product_01, Product 01, A4_Grp_01, A4 Grp 01
                    clean_name = name.lower().replace(" ", "_")
                    
                    if clean_name.startswith("product_") or clean_name.startswith("a4_grp_"):
                        # Normalize Key to standard "Product_01" format for consistency
                        # If it's "Product 01", we want to store it as "Product_01" if possible, 
                        # or just keep original name but normalized?
                        # Excel has "Product_01". We must match that.
                        
                        # Extract Number
                        match = re.search(r'(\d+)', clean_name)
                        if match:
                            num = int(match.group(1))
                            suffix = f"{num:02d}"
                            if "a4" in clean_name:
                                norm_key = f"A4_Grp_{suffix}"
                            else:
                                norm_key = f"Product_{suffix}"
                                
                            print(f"    -> MATCH: {name} mapped to {norm_key}")
                            
                            group_data = self._parse_group(layer)
                            extracted_data["groups"][norm_key] = group_data
                        else:
                            print(f"    -> IGNORED: {name} (No number found)")
                    
                    # Continue recursion
                    traverse(layer, depth + 1)

        traverse(psd)
        print(f"--- Scan Complete: {len(extracted_data['groups'])} groups found ---")
        
        # 3. Save JSON
        json_path = os.path.join(self.output_dir, f"scan_{page_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
        return {
            "page": page_name,
            "json_path": json_path,
            "preview_path": preview_path,
            "group_count": len(extracted_data["groups"])
        }

    def _parse_group(self, group_layer):
        data = {
            "bbox": list(group_layer.bbox), # (left, top, right, bottom)
            "layers": {}
        }
        
        # We need to find text layers inside
        # Flatten children for easier search
        # psd-tools iterators are depth-first
        
        for layer in group_layer.descendants():
            if layer.kind == "type": # Text Layer
                text = layer.text.strip()
                # Clean up name: remove " copy", trim
                name = re.sub(r'\s+copy\s*\d*$', '', layer.name, flags=re.IGNORECASE).strip()
                
                # We store it by layer name (e.g., nazev_01A)
                # Note: There might be duplicates if user manually duped layers with same name.
                # We overwrite or append? Overwrite is simpler for matching logic.
                data["layers"][name.lower()] = {
                    "text": text,
                    "visible": layer.visible
                }
                
        return data
