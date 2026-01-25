import json
import os
from psd_tools import PSDImage

def verify_schema():
    schema_path = "conductor/psd_schema.json"
    psd_path = "Letak W Page 10 NÁPOJE - -cx_v2.psd"
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
        
    print(f"Verifying schema '{schema['template_id']}' against '{psd_path}'...")
    
    try:
        psd = PSDImage.open(psd_path)
    except Exception as e:
        print(f"Failed to open PSD: {e}")
        return

    # Check Product_01
    group_name = "Product_01"
    suffix = "01"
    
    # Find group
    product_group = None
    for layer in psd:
        if layer.name == group_name:
            product_group = layer
            break
            
    if not product_group:
        print(f"CRITICAL: Group {group_name} not found in PSD!")
        return

    print(f"Group {group_name} found. Checking layers...")
    
    # Flatten layers in group for easy search
    flat_layers = {l.name: l for l in product_group.descendants()}
    
    all_good = True
    for field in schema['layers']:
        # Construct expected layer name
        # The schema uses "Pricetag_XX/cena_XX/cena_XXA" notation for hierarchy or just suffix?
        # My schema used paths: "Pricetag_XX/cena_XX/cena_XXA"
        # Let's support both: direct name match or path match.
        
        # For this verification, we usually just care about the leaf node name
        path_template = field['layer_suffix']
        # Extract leaf name (last part)
        leaf_template = path_template.split('/')[-1]
        
        expected_name = leaf_template.replace("XX", suffix)
        
        if expected_name in flat_layers:
            print(f"  [OK] Found '{expected_name}' ({field['logical_name']})")
        else:
            print(f"  [FAIL] Missing '{expected_name}' ({field['logical_name']})")
            # Debug: print similar names?
            all_good = False
            
    if all_good:
        print("\nSUCCESS: Schema matches PSD structure for Product_01.")
    else:
        print("\nWARNING: Some schema fields are missing in the PSD.")

if __name__ == "__main__":
    verify_schema()
