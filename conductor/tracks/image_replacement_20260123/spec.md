# Specification: Image Replacement Improvements

## 1. Problem Analysis
- **Current Logic:** `builder.jsx` assumes the target layer is a Smart Object and uses `placedLayerReplaceContents`. This fails for raster layers or if the layer structure doesn't match the hardcoded names ("image", "obraz", etc.).
- **User Requirement:** Support "Place & Hide" strategy to handle various placeholder types (Raster, Shape, Smart Object) and avoid distortion.

## 2. "Place & Hide" Strategy
The new logic should:
1.  **Locate Placeholder:** Find the layer/group intended for the image.
    -   Support explicit naming (e.g., `image_01`, `obraz_01`, `image`, `obraz`).
    -   Support "fuzzy" matching within the Product Group (e.g., `Product_01`).
2.  **Get Geometry:** Measure the Bounds of the placeholder (X, Y, Width, Height).
3.  **Place Image:** Import the new product image file as a *new* layer/Smart Object.
4.  **Resize & Align:** 
    -   Resize the new image to fit within the placeholder's bounds (contain or cover, likely "contain" for products).
    -   Center the new image over the placeholder.
5.  **Hide Placeholder:** Toggle the visibility of the original placeholder layer to `false`.

## 3. Layer Targeting
- The script must recursively search for the image layer within the specific `Product_XX` group.
- It should handle cases where the layer name includes the suffix (e.g., `obraz_01A`) dynamically.

## 4. Technical Implementation (JSX)
- Use `app.activeDocument.place(file)` to bring in the image.
- Use `layer.bounds` to get coordinates.
- Use `layer.resize(w, h)` and `layer.translate(dx, dy)` for positioning.
