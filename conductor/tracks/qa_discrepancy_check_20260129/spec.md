# Specification: QA Discrepancy Checker

## 1. Data Extraction (Source: PSD Files)
We need a high-performance extraction method that doesn't tie up the user's Photoshop instance.
-   **Method:** Python `psd-tools` library.
-   **Input:** User selects Folder or File list via UI.
-   **Process:**
    -   Parse PSD layer structure.
    -   Identify Groups (Product_XX, A4_Grp_XX).
    -   Extract Text content from children layers.
    -   **Render:** Generate 1600px PNG preview of the whole page.
    -   **Metadata:** Capture bounding box coordinates (x, y, w, h) for each group for the "Spotlight" feature.
-   **Output:** 
    -   `workspaces/qa/scans/scan_Page_XX.json` (Data + Coordinates).
    -   `frontend_static/previews/Page_XX.png` (Visual).

## 2. Reference Data & Write-back (Excel)
The extraction results must be visible in Excel for manual inspection if needed.
-   **Write-back Target:** Columns **BA** onwards.
-   **Mapping:** Same structure as Automation (Name, Price A/B, EAN, etc.), prefixed with `ACTUAL_`.
-   **Logic:**
    -   Iterate extracted PSD Groups.
    -   Match with `PSD_Group` column (AM).
    -   Write extracted text into the corresponding row's `BA+` columns.

## 3. Comparison Logic ("Check")
-   **Trigger:** "Check" button in UI.
-   **Comparison:** Row-by-Row comparison of `EXPECTED` (Columns AM-AY) vs `ACTUAL` (Columns BA+).
-   **Rules:**
    -   **Prices / EANs:** Strict Equality.
    -   **Text (Names/Desc):** Smart Fuzzy Match.
        -   Allow whitespace/case differences.
        -   Allow ~10-20% token difference (e.g. line breaks, minor abbreviations).
        -   Score < 80% = **MISMATCH**.
-   **Action on Mismatch:**
    -   **Highlight:** Fill Columns **D through H** (Source Data) with "Orange, Accent 2, Lighter 40%".
    -   **Link:** Insert Hyperlink in the highlighted cells.
        -   Target: `http://localhost:5173/qa/inspect?page={page}&group={group}`.

## 4. User Interface
-   **Tab:** "Leták checker".
-   **State:** Disabled until Layout Automation is complete.
-   **Workflow:**
    1.  **Import:** Select PSDs -> Progress Bar -> Results (Thumbnails).
    2.  **Check:** Button -> Updates Excel -> Shows summary (X Discrepancies found).
-   **Inspection View (`/qa/inspect`):**
    -   Displays the Page Preview.
    -   **Overlay:** Semi-transparent black layer over the image.
    -   **Spotlight:** The specific Group's bounding box is "cut out" (fully bright/visible) to focus attention.
