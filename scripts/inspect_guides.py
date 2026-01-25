from psd_tools import PSDImage
import sys

def inspect_guides(file_path):
    try:
        psd = PSDImage.open(file_path)
        GUIDE_RESOURCE_ID = 1032
        if GUIDE_RESOURCE_ID in psd.image_resources:
            res = psd.image_resources[GUIDE_RESOURCE_ID]
            data = res.data
            print(f"data.vertical: {data.vertical} ({type(data.vertical)})")
            print(f"data.horizontal: {data.horizontal} ({type(data.horizontal)})")
            
            # Maybe it has a 'guides' attribute after all?
            if hasattr(data, 'guides'):
                print("data.guides exists")
            
            # Let's check 'data.data' which was in the dir()
            if hasattr(data, 'data'):
                print(f"data.data type: {type(data.data)}")
                for item in data.data:
                    print(f"Item: {item}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    path = "Letak W Page 10 NÁPOJE - -cx_v2.psd"
    inspect_guides(path)
