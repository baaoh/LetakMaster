# Implementation Plan: QA Discrepancy Checker

## Phase 1: Backend Infrastructure (Python)
- [x] **Dependencies:** Ensure `psd-tools` and fuzzy matching lib available.
- [x] **PSD Reader (`app/qa/psd_reader.py`):**
    -   Implemented `extract_data_from_psd(file_path)`.
    -   Handles `Product_XX` / `A4_Grp_XX`.
    -   Renders PNG preview (1600px).
    -   Extracts bounding box coordinates.
- [x] **QA Service (`app/qa/qa_service.py`):**
    -   Bridge between Reader and Excel.
    -   Implemented `run_import(files)` -> Calls Reader -> Structures Data.

## Phase 2: Excel Integration
- [x] **Write-Back Logic:**
    -   Extended `QAService` to write "Actual" data to columns **BA onwards**.
    -   Headers: `ACTUAL_Nazev_A`, `ACTUAL_Nazev_B`, etc.
- [x] **Comparison & Formatting:**
    -   Implemented `run_check()`.
    -   Reads **AM-AY** (Expected) vs **BA+** (Actual).
    -   Applies Fuzzy Match logic (difflib).
    -   Applies **Orange Highlight** to Columns **D-H** for mismatched rows.
    -   Inserts **Hyperlinks** to `http://localhost:5173/qa/inspect?...`.

## Phase 3: Frontend UI
- [x] **Tab "Leták checker":**
    -   Added to main navigation (conditional visibility based on history).
- [x] **Import View:**
    -   "Import PSD Folder" button.
    -   Grid of imported page thumbnails.
- [x] **Check Action:**
    -   "Run Check" button -> Calls backend -> Updates Excel.
- [x] **Inspection View (`QAInspect.tsx`):**
    -   Route `/qa/inspect`.
    -   Canvas/Image loader.
    -   "Spotlight" overlay logic using URL params `page` & `group`.

## Phase 4: Integration & Testing
- [x] **API Endpoints:** `POST /qa/import`, `POST /qa/check`, `GET /qa/inspect`.
- [ ] **Verification:** Run a full flow. Modify a text layer in PSD, run check, verify Excel highlights and Link works.
