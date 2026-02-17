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

        # 2. Extract Flat Layer List
        extracted_data = {
            "page_name": page_name,
            "layers": []
        }

        print(f"--- Scanning All Layers for {filename} ---")

        # Recursive traversal to flatten all layers
        def traverse(layers, parent_name="Root"):
            for layer in layers:
                if layer.is_group():
                    # Recurse into groups
                    traverse(layer, parent_name=layer.name)
                elif layer.kind == "type":
                    # Capture Text Layer
                    text = layer.text.strip()
                    if text: # Only capture if it has text
                        # Clean up name: remove " copy", trim
                        clean_name = re.sub(r'\s+copy\s*\d*$', '', layer.name, flags=re.IGNORECASE).strip()
                        
                        extracted_data["layers"].append({
                            "name": clean_name,
                            "text": text,
                            "visible": layer.visible,
                            "bbox": list(layer.bbox),
                            "parent_group": parent_name
                        })

        traverse(psd)
        print(f"--- Scan Complete: {len(extracted_data['layers'])} text layers found ---")
        
        # 3. Save JSON
        json_path = os.path.join(self.output_dir, f"scan_{page_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
        return {
            "page": page_name,
            "json_path": json_path,
            "preview_path": preview_path,
            "layer_count": len(extracted_data["layers"])
        }

