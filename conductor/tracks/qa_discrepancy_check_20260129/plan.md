# Implementation Plan: QA Discrepancy Checker

## Phase 1: Infrastructure & Dependencies
- [x] **Dependencies:** Ensure `psd-tools` available.
- [ ] **Fuzzy Matching:** Add `thefuzz` to `requirements.txt` for flexible text comparison.
- [ ] **State-Bound Storage:**
    -   Update `QAService` to resolve paths relative to `workspaces/state_{id}/qa/`.
    -   Ensure `PSDReader` saves previews and JSONs in this state-specific folder.

## Phase 2: Refined Parsing & Matching (CRITICAL)
- [ ] **PSD Reader Refactor (`app/qa/psd_reader.py`):**
    -   Change output format: Instead of trying to guess groups, output a **Flat List** of all text layers.
    -   Include: Layer Name, Text Content, Visibility, Bounding Box, Parent Group Name (for context).
- [ ] **QA Matcher Logic (`app/qa/qa_matcher.py`):**
    -   New service to bridge `build_page_X.json` (Expected) and `scan_Page_X.json` (Actual).
    -   **Algorithm:**
        1.  Load Build Plan for the page.
        2.  For each expected attribute (Nazev A, Price, EAN, etc.):
        3.  Search ALL visible PSD text layers.
        4.  Score matches using `thefuzz` (Text Similarity) + Layer Name Heuristics.
        5.  Select best candidate.
    -   **Metric:** Count "Visible, Matched Attributes" rather than just "Groups".

## Phase 3: Excel Integration (Write-Back)
- [ ] **Write-Back Logic:**
    -   Update `QAService` to use the output of `QAMatcher`.
    -   Map matched values to **BA onwards**.
    -   Headers must match: `PSD_Nazev_A` -> `ACTUAL_Nazev_A`, etc.
- [ ] **Comparison:**
    -   Update `run_check()` to compare the new "Fuzzy Matched" Actuals vs Expected.
    -   Highlight discrepancies in Orange.

## Phase 4: Frontend & UI
- [ ] **Frontend Update:**
    -   Ensure "Import" triggers the new `run_import` which now requires a `state_id` (or derives it).
    -   Update Inspection View to handle the new JSON structure if necessary.

## Phase 5: Verification
- [ ] **Full Flow Test:**
    1.  Sync Master Excel (State X).
    2.  Generate Build Plans.
    3.  Modify PSD (Simulate manual edits).
    4.  Run QA Check.
    5.  Verify Excel accurately reflects the PSD content despite loose grouping.
