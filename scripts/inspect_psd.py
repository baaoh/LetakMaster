from psd_tools import PSDImage
import sys
import os

def inspect_psd(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    try:
        psd = PSDImage.open(file_path)
        print(f"PSD File: {file_path}")
        print(f"Size: {psd.width}x{psd.height}")
        # count layers recursively
        layers = list(psd.descendants())
        print(f"Layers count: {len(layers)}")
        print("\nLayers list (first 50):")
        for i, layer in enumerate(layers):
            if i >= 50:
                print("... (more layers truncated)")
                break
            
            kind_info = f" [{layer.kind}]" if hasattr(layer, 'kind') else ""
            text_info = ""
            if layer.kind == 'type' and hasattr(layer, 'text'):
                # Limit text output
                text_content = layer.text.strip().replace('\n', ' ')[:50]
                text_info = f" - Text: {text_content}"
            
            print(f"- {layer.name}{kind_info}{text_info}")

    except Exception as e:
        print(f"Error reading PSD: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Use the filename from command line if provided, else default
    path = sys.argv[1] if len(sys.argv) > 1 else 'Letak W Page 10 NÁPOJE - -cx.psd'
    inspect_psd(path)
