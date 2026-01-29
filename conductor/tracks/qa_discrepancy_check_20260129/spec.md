# Specification: QA Discrepancy Checker

## 1. Data Extraction (Source: PSD)
We need a robust way to read "What is currently on the page".
-   **Method:** ExtendScript (`scripts/scanner.jsx`).
-   **Input:** Active Photoshop Document.
-   **Output:** JSON file (`workspaces/scans/scan_Page_XX.json`).
-   **Structure:**
    ```json
    {
      "page": 1,
      "groups": {
        "Product_01": {
          "nazev_01A": "Text Content",
          "cena_01A": "99",
          "cena_01B": "90",
          "visible": true
        },
        "A4_Grp_02": { ... }
      }
    }
    ```

## 2. Reference Data (Source: Excel)
We need to fetch the *live* data from the Master Excel.
-   **Method:** `AutomationService.enrich_active_workbook` logic (conceptually), but specifically fetching data for comparison.
-   **Mapping:** 
    -   We iterate the Excel rows.
    -   We look for the `PSD_Group` column (Column AM / 38).
    -   If `PSD_Group` matches a key in the PSD Scan (e.g., `Product_01`), we compare fields.

## 3. Comparison Logic
-   **Fields to Check:**
    -   **Name:** Fuzzy match (allow minor spacing diffs).
    -   **Price:** Exact match on Integer/Decimal parts.
    -   **EAN:** Exact match.
    -   **Visibility:** Check if "Subtitle" is visible in PSD but empty in Excel (or vice versa).
-   **Status Levels:**
    -   ✅ **MATCH:** Data is identical.
    -   ⚠️ **MINOR:** Case difference or extra whitespace.
    -   ❌ **MISMATCH:** Price or Name differs significantly.
    -   ❓ **MISSING:** Group exists in Excel but not in PSD (or vice versa).

## 4. User Interface
-   **Backend:** `POST /qa/scan` (triggers JSX), `GET /qa/report/{page_id}`.
-   **Frontend:**
    -   "QA" Tab.
    -   "Scan Current Page" Button.
    -   Result Table:
        | Group | Layer | PSD Value | Excel Value | Status |
        |-------|-------|-----------|-------------|--------|
        | Prod_01 | Price | 99.90 | 109.90 | ❌ |
