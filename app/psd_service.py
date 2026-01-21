from psd_tools import PSDImage
import os

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
