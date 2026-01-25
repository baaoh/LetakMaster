from psd_tools import PSDImage
import sys
import copy
import os

def duplicate_product_group(input_path, output_path):
    try:
        psd = PSDImage.open(input_path)
        print(f"Loaded {input_path}")

        # Find Product_01 group
        product_01 = None
        for layer in psd:
            if layer.name == 'Product_01':
                product_01 = layer
                break
        
        if not product_01:
            print("Error: 'Product_01' group not found.")
            return

        print("Found 'Product_01', attempting duplication...")

        # NOTE: psd-tools usually does not support adding new layers easily. 
        # We will try to manipulate the internal list if possible, or deepcopy.
        # This is experimental.
        
        try:
            # We need to replicate this 15 times (for 02 to 16)
            for i in range(2, 17):
                suffix = f"_{i:02d}"
                print(f"Creating Product{suffix}...")
                
                # Deep copy the layer/group
                # psd-tools layers are complex objects linked to binary data. 
                # copy.deepcopy might not work or might be insufficient.
                new_group = copy.deepcopy(product_01)
                new_group.name = f"Product{suffix}"
                
                # Recursively rename children
                def rename_children(layer, old_s, new_s):
                    if layer.is_group():
                        for child in layer:
                            rename_children(child, old_s, new_s)
                    
                    if layer.name and old_s in layer.name:
                        layer.name = layer.name.replace(old_s, new_s)
                
                rename_children(new_group, "_01", suffix)
                
                # Append to PSD internal layer list
                # Depending on version, this might be a list or require internal access
                # For psd-tools v1.9+, psd is list-like
                psd._layers.append(new_group) 
                
        except Exception as e:
            print(f"Duplication failed: {e}")
            import traceback
            traceback.print_exc()
            return

        print(f"Saving to {output_path}...")
        psd.save(output_path)
        print("Done.")

    except Exception as e:
        print(f"General Error: {e}")

if __name__ == "__main__":
    input_file = "Letak W Page 10 NÁPOJE - -cx_v2.psd"
    output_file = "Letak W Page 10 NÁPOJE - -cx_v2_16products.psd"
    duplicate_product_group(input_file, output_file)
