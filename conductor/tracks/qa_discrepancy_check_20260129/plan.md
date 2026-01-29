# Implementation Plan: QA Discrepancy Checker

## Phase 1: PSD Scanner (`scripts/scanner.jsx`)
- [ ] **Create Script:** Develop `scripts/scanner.jsx`.
    -   Function `scanDocument()`:
        -   Iterate all layer sets (Groups).
        -   Identify "Product Groups" (Product_*, A4_Grp_*).
        -   Inside group, iterate text layers.
        -   Store Name + Text Content.
    -   Output: Write to `workspaces/scans/last_scan.json`.

## Phase 2: Backend Comparison (`app/qa_service.py`)
- [ ] **Service Class:** Create `QAService`.
- [ ] **Load Excel:** Reuse `AutomationService` or `ExcelService` to read current Master Excel state (specifically columns AM-AY for mapping).
- [ ] **Load Scan:** Read `last_scan.json`.
- [ ] **Diff Logic:**
    -   Iterate Scan Groups.
    -   Find corresponding Row in Excel (by `PSD_Group` column).
    -   Compare `PSD Content` vs `Excel Content` (mapped via `HEADERS` logic).
    -   Generate Report List.

## Phase 3: API & Frontend
- [ ] **API:**
    -   `POST /qa/scan`: Triggers `scanner.jsx` (via `app.utils.run_script`).
    -   `GET /qa/report`: Returns the comparison result.
- [ ] **Frontend (React):**
    -   New Component `QAView`.
    -   "Scan" Button (calls `/qa/scan` -> waits -> calls `/qa/report`).
    -   Table display of discrepancies.

## Phase 4: Integration
- [ ] **Register:** Add QA tool to the main Dashboard/Launcher.
- [ ] **Verify:** Test with a modified Excel file (change a price) and verify the mismatch is caught.
