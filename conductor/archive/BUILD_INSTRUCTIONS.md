# Photoshop Build Pipeline

This pipeline automates the creation of flyer pages from Excel data.

## Workflow

1.  **Prepare Excel Data**
    *   Ensure `Copy of letak prodejna 2026 NEW FINAL.xls` is updated.
    *   Columns: `HERO` (L), `Page` (V), `Product` (D), `Price` (W).

2.  **Run Allocation (Enrichment)**
    *   Calculates layout for every page.
    *   Writes `PSD_Allocation` to **Column X** in Excel.
    ```bash
    python_embed\python.exe scripts/enrich_excel.py
    ```

3.  **Generate Build Plan**
    *   Extracts data for a specific page (e.g., Page 25) into a JSON file.
    ```bash
    python_embed\python.exe scripts/generate_build_json.py 25
    ```
    *   Output: `build_page_25.json`

4.  **Run Photoshop Builder**
    *   Open `Letak W Page 10 NÁPOJE - -cx_v2.psd` in Adobe Photoshop.
    *   Run Script: `File > Scripts > Browse...` -> Select `scripts/builder.jsx`.
    *   *Note: Ensure `builder.jsx` points to the correct JSON path or place JSON in root.*

## Architecture
*   **`SlotAllocator`**: Handles the "Tetris" logic (fitting 1x1, 1x2, 2x2 items).
*   **`builder.jsx`**:
    *   Updates text layers (`nazev_XXA`, `cena_XXA`).
    *   Handles `HERO` logic by hiding overlapped groups (e.g., if Product_01 is 2x2, it hides Product_02, 05, 06).
