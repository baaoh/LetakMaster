from psd_tools import PSDImage
import sys

def analyze_layout(file_path):
    try:
        psd = PSDImage.open(file_path)
        print(f"--- Detailed Layout Analysis: {file_path}")
        print(f"Canvas: {psd.width}x{psd.height} px\n")

        # Define the target group
        target_name = "Product_01"
        target_group = None
        for layer in psd:
            if layer.name == target_name:
                target_group = layer
                break
        
        if not target_group:
            print(f"Error: {target_name} not found.")
            return

        print(f"Structure for {target_name}:")
        print(f"Overall Box: Pos ({target_group.left}, {target_group.top}), Size {target_group.width}x{target_group.height}")
        
        # Recursive function to walk the tree
        def walk(layers, level=1):
            for layer in layers:
                indent = "  " * level
                kind = f"[{layer.kind}]"
                coords = f"Pos: ({layer.left}, {layer.top}) Size: {layer.width}x{layer.height}"
                text = f" | Text: '{layer.text.strip()[:40]}'" if layer.kind == 'type' and hasattr(layer, 'text') and layer.text else ""
                
                if layer.width > 0 or layer.is_group():
                    print(f"{indent}- {layer.name:<20} {kind:<12} | {coords}{text}")
                
                if layer.is_group():
                    walk(layer, level + 1)

        walk(target_group)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_layout("Letak W Page 10 NÁPOJE - -cx_v2.psd")