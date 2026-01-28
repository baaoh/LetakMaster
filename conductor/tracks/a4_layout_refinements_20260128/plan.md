# Implementation Plan: A4 Layout Refinements

## Phase 1: Python Enrichment (`app/automation.py`)
- [x] **Smart Title Splitter:**
    -   Modify `_enrich_logic`.
    -   Implement logic to check `PSD_Nazev_A` length.
    -   If > 20 chars, split and move remainder to `PSD_Nazev_B`.
- [x] **Subtitle Visibility:**
    -   Implemented in `_write_page_json`: if `nazev_XXB` is empty string, add `visibility: { "nazev_XXB": false }`.

## Phase 2: Builder Script (`scripts/builder.jsx`)
- [x] **A4 Group Offset:**
    -   In `processA4Groups`, calculate height and translate group.
- [x] **Image Layouting:**
    -   Update `replaceProductImageAM`.
    -   Resizes to 500x500px.
    -   Positions to the right of the group side-by-side.
- [x] **Subtitle Visibility:**
    -   Updated visibility loop and text matching to support `_A`/`_B` suffixes.

## Phase 3: Verification
- [x] Unit tests for title splitting and visibility logic in `tests/test_a4_refinements.py`.
- [ ] Test on real A4 page in Photoshop.
