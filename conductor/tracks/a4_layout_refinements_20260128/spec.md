# Specification: A4 Layout Refinements

## 1. Group Layout (Photoshop)
*   **Problem:** `A4_Grp_XX` duplicates stack directly on top of `A4_01`.
*   **Requirement:** Each subsequent duplicate must be vertically offset from the previous one.
*   **Logic:**
    *   `Offset Y = Previous Group Bottom + Margin`.
    *   Alternatively, a fixed offset `(e.g., 200px)` per step if group height is constant.
    *   Implemented in `scripts/builder.jsx` during `processA4Groups`.

## 2. Image Placement (Photoshop)
*   **Problem:** Images are placed with original size and position, potentially overlapping or obscuring text.
*   **Requirement:**
    *   **Size:** Resize to **500x500px** (maintain aspect ratio within box? or force?). User said "500x500 px". Usually means "Fit within 500x500" or "Resize long edge to 500". "Smart objects so scaling is lossless".
    *   **Position:** "Next to the group pricetag to the right".
    *   **Layout:** "Don't overlay each other". If multiple images, tile them (e.g., horizontal row starting from Group Right Edge).
*   **Implementation:** Update `replaceProductImageAM` in `scripts/builder.jsx`.

## 3. Title & Subtitle Logic (Python Enrichment)
*   **Problem:** Long titles overflow; subtitles sometimes have boilerplate or are missing.
*   **Requirement:**
    *   **Parsing:**
        *   Input: `Product Name` (Col D) and `Description` (Col E).
        *   If `Product Name` > **20 characters**:
            *   Split text at the nearest word boundary before 20 chars.
            *   Part 1 -> `PSD_Nazev_A` (Main Title).
            *   Part 2 + Existing Description -> `PSD_Nazev_B` (Subtitle).
    *   **Visibility:**
        *   If `PSD_Nazev_B` is empty (after split logic), explicitly set its visibility to `FALSE`.
        *   Ensure `builder.jsx` respects this visibility flag for `nazev_XXB`.

## 4. Subtitle Cleaning
*   **Requirement:** "filled with some nonsense".
*   **Approach:** Define a list of "boilerplate" strings (e.g., "doplněk", "popis") to strip during enrichment. If result is empty, hide layer.
