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
        try:
            image = psd.composite()
            if image:
                # Resize
                width, height = image.size
                if width > 1600:
                    ratio = 1600 / width
                    new_height = int(height * ratio)
                    image = image.resize((1600, new_height), Image.Resampling.LANCZOS)
                
                image.save(preview_path, "PNG")
                print(f"Preview saved: {preview_path}")
            else:
                print("Warning: Could not generate composite image.")
        except Exception as e:
            print(f"Preview generation failed: {e}")

        # 2. Extract Data & Coordinates
        extracted_data = {
            "page_name": page_name,
            "groups": {}
        }

        # Recursive traversal
        def traverse(layers):
            for layer in layers:
                if layer.is_group():
                    name = layer.name
                    # Check for Product Groups (Product_XX, A4_Grp_XX)
                    if name.startswith("Product_") or name.startswith("A4_Grp_"):
                        # Capture this group
                        group_data = self._parse_group(layer)
                        extracted_data["groups"][name] = group_data
                    
                    # Continue recursion (in case nested, though usually Products are top level or under "Products")
                    traverse(layer)

        traverse(psd)
        
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
