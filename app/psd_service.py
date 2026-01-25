from psd_tools import PSDImage
import os
import re
import datetime
from sqlalchemy.orm import Session
from app.database import PageAsset

class PSDService:
    def read_layers(self, psd_path: str):
        """
        Reads all text layers from a PSD file and returns their names and content.
        """
        if not os.path.exists(psd_path):
            # For the sake of mock tests, we allow non-existent paths if mocked
            pass

        layers_data = {}
        psd = PSDImage.open(psd_path)
        
        # descendants() gives a flat list of all layers including those in groups
        for layer in psd.descendants():
            if layer.kind == 'type': # This is a text layer
                layers_data[layer.name] = layer.text
                
        return layers_data

    def update_layers(self, template_path: str, data_mapping: dict, output_path: str):
        """
        Updates text layers in a PSD template based on data_mapping {layer_name: new_text}.
        Saves the result to output_path.
        """
        psd = PSDImage.open(template_path)
        
        for layer in psd.descendants():
            if layer.kind == 'type' and layer.name in data_mapping:
                layer.text = data_mapping[layer.name]
                
        psd.save(output_path)
        return output_path

    def read_guides(self, psd_path: str) -> dict:
        """
        Reads guides from a PSD file.
        Returns a dict with 'vertical' and 'horizontal' lists of pixel coordinates.
        """
        guides = {"vertical": [], "horizontal": []}
        
        if not os.path.exists(psd_path):
            return guides

        try:
            psd = PSDImage.open(psd_path)
            GUIDE_RESOURCE_ID = 1032
            
            if hasattr(psd, 'image_resources') and GUIDE_RESOURCE_ID in psd.image_resources:
                res = psd.image_resources[GUIDE_RESOURCE_ID]
                # In psd-tools, resource.data is the parsed object (GridGuidesInfo)
                # GridGuidesInfo.data is the list of (location, orientation)
                if hasattr(res, 'data') and hasattr(res.data, 'data'):
                    for location, orientation in res.data.data:
                        # Orientation 0 = Vertical, 1 = Horizontal
                        # Location is in 1/32 pixels
                        pixel_loc = location / 32.0
                        if orientation == 0:
                            guides["vertical"].append(pixel_loc)
                        elif orientation == 1:
                            guides["horizontal"].append(pixel_loc)
                            
            guides["vertical"].sort()
            guides["horizontal"].sort()
            
        except Exception as e:
            print(f"Error reading guides from {psd_path}: {e}")
            
        return guides

    def render_preview(self, psd_path: str, output_path: str):
        """
        Renders a composite preview of the PSD and saves as PNG/JPG.
        """
        if not os.path.exists(psd_path):
            raise FileNotFoundError(f"PSD not found: {psd_path}")
            
        print(f"Rendering preview for {psd_path}...")
        psd = PSDImage.open(psd_path)
        image = psd.composite()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        image.save(output_path)
        print(f"Preview saved to {output_path}")
        return output_path

    def scan_and_index_psds(self, root_path: str, db: Session, preview_dir: str):
        """
        Scans root_path for '*Page XX*.psd' files.
        Updates PageAsset table.
        Renders previews if missing or stale.
        """
        scan_results = []
        
        for root, dirs, files in os.walk(root_path):
            # Skip hidden or system folders
            if ".git" in root or "__pycache__" in root or "node_modules" in root:
                continue
                
            for filename in files:
                if not filename.lower().endswith(".psd"):
                    continue
                
                # Match "Page XX"
                match = re.search(r"Page\s*(\d+)", filename, re.IGNORECASE)
                if match:
                    page_num = int(match.group(1))
                    full_path = os.path.abspath(os.path.join(root, filename))
                    
                    # Check DB
                    asset = db.query(PageAsset).filter_by(page_number=page_num).first()
                    
                    if not asset:
                        asset = PageAsset(
                            page_number=page_num,
                            psd_filename=filename,
                            psd_path=full_path
                        )
                        db.add(asset)
                    else:
                        asset.psd_path = full_path
                        asset.psd_filename = filename
                    
                    # Check Preview Freshness
                    preview_filename = f"page_{page_num}.png"
                    preview_full_path = os.path.join(preview_dir, preview_filename)
                    
                    file_mtime = os.path.getmtime(full_path)
                    should_render = False
                    
                    if not asset.preview_path or not os.path.exists(asset.preview_path):
                        should_render = True
                    elif asset.last_rendered:
                        # Check timestamp
                        last_render_ts = asset.last_rendered.timestamp()
                        if file_mtime > last_render_ts:
                            should_render = True
                    
                    if should_render:
                        try:
                            self.render_preview(full_path, preview_full_path)
                            # Update Asset
                            # Relative path for frontend serving (e.g., "previews/page_1.png")
                            # Assuming preview_dir is inside frontend_static/
                            
                            # We store absolute path for backend, but might need URL conversion
                            asset.preview_path = preview_full_path
                            asset.last_rendered = datetime.datetime.fromtimestamp(file_mtime) # Use file time as sync point? Or now? Now is better.
                            asset.last_rendered = datetime.datetime.now()
                            scan_results.append({"page": page_num, "status": "rendered"})
                        except Exception as e:
                            print(f"Failed to render Page {page_num}: {e}")
                            scan_results.append({"page": page_num, "status": "error", "error": str(e)})
                    else:
                        scan_results.append({"page": page_num, "status": "cached"})
        
        db.commit()
        return scan_results
