from psd_tools import PSDImage
import sys
import os

def update_text_layer(psd_path, output_path, layer_name, new_text):
    try:
        psd = PSDImage.open(psd_path)
        print(f"Loaded {psd_path}")
        
        found = False
        for layer in psd.descendants():
            if layer.name == layer_name and layer.kind == 'type':
                print(f"Found layer '{layer_name}'. Current text: '{layer.text.strip()}'")
                layer.text = new_text
                found = True
                # Usually we only want to update the first match or all? Let's keep going just in case.
        
        if not found:
            print(f"Error: Text layer '{layer_name}' not found.")
            return

        print(f"Saving changes to {output_path}...")
        psd.save(output_path)
        print("Done.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    input_file = "Letak W Page 10 NÁPOJE - -cx_v2.psd"
    output_file = "Letak_v2_updated.psd"
    update_text_layer(input_file, output_file, "nazev_01A", "Máslo")
