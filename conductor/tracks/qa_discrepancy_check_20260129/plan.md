# Implementation Plan: QA Discrepancy Checker

## Phase 1: Backend Infrastructure (Python)
- [ ] **Dependencies:** Ensure `psd-tools` and fuzzy matching lib (`thefuzz` or `difflib`) are available.
- [ ] **PSD Reader (`app/qa/psd_reader.py`):**
    -   Implement `extract_data_from_psd(file_path)`.
    -   Logic to parse `Product_XX` / `A4_Grp_XX`.
    -   Logic to render PNG preview (1600px).
    -   Logic to extract bounding box coordinates.
- [ ] **QA Service (`app/qa/qa_service.py`):**
    -   Bridge between Reader and Excel.
    -   Implement `import_psd_folder(folder_path)` -> Calls Reader -> Structures Data.

## Phase 2: Excel Integration
- [ ] **Write-Back Logic:**
    -   Extend `ExcelService` to write "Actual" data to columns **BA onwards**.
    -   Headers: `PSD_ACTUAL_Group`, `PSD_ACTUAL_Nazev_A`, etc.
- [ ] **Comparison & Formatting:**
    -   Implement `compare_and_highlight(book)`.
    -   Read **AM-AY** (Expected) vs **BA+** (Actual).
    -   Apply Fuzzy Match logic.
    -   Apply **Orange Highlight** to Columns **D-H** for mismatched rows.
    -   Insert **Hyperlinks** to `http://localhost:5173/qa/inspect?...`.

## Phase 3: Frontend UI
- [ ] **Tab "Leták checker":**
    -   Add to main navigation (conditional visibility).
- [ ] **Import View:**
    -   "Select Folder" / "Select Files" button.
    -   Grid of imported page thumbnails.
- [ ] **Check Action:**
    -   "Run Check" button -> Calls backend -> Updates Excel.
    -   Display summary toast ("5 Mismatches found").
- [ ] **Inspection View (`QAInspect.tsx`):**
    -   Route `/qa/inspect`.
    -   Canvas/Image loader.
    -   "Spotlight" overlay logic using URL params `page` & `group` -> fetch coordinates from backend.

## Phase 4: Integration & Testing
- [ ] **API Endpoints:** `POST /qa/import`, `POST /qa/check`, `GET /qa/coords/{page}/{group}`.
- [ ] **Verification:** Run a full flow. Modify a text layer in PSD, run check, verify Excel highlights and Link works.
