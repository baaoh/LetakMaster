import os
import random
from PIL import Image, ImageDraw, ImageFont

# List of IDs to generate images for
ids = [
    "5061258",
    "5061261",
    "5061265",
    "5060305",
    "5062557",
    "5062558",
    "5062506",
    "5062519",
    "5061223",
    "5065466",
    "5060070",
    "5060069",
    "5050173"
]

output_dir = os.path.join("workspaces", "images")
os.makedirs(output_dir, exist_ok=True)

def get_pastel_color():
    # Generate a random pastel color
    # High RGB values mixed with white
    r = random.randint(200, 255)
    g = random.randint(200, 255)
    b = random.randint(200, 255)
    return (r, g, b)

def generate_image(file_id):
    width, height = 400, 400
    color = get_pastel_color()
    
    img = Image.new('RGB', (width, height), color=color)
    d = ImageDraw.Draw(img)
    
    try:
        # Try to load Arial, size 40
        font = ImageFont.truetype("arial.ttf", 60)
    except IOError:
        # Fallback to default if Arial not found
        print("Arial font not found, using default.")
        font = ImageFont.load_default()

    # Calculate text position to center it
    text = str(file_id)
    
    # Get text bounding box
    left, top, right, bottom = d.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top
    
    x = (width - text_width) / 2
    y = (height - text_height) / 2
    
    # Draw text in black
    d.text((x, y), text, fill=(0, 0, 0), font=font)
    
    filename = os.path.join(output_dir, f"{file_id}.png")
    img.save(filename)
    print(f"Generated {filename}")

if __name__ == "__main__":
    print(f"Generating images in {output_dir}...")
    for file_id in ids:
        generate_image(file_id)
    print("Done.")
