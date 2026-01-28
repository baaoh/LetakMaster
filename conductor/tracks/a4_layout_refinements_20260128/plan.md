# Implementation Plan: A4 Layout Refinements

## Phase 1: Python Enrichment (`app/automation.py`)
- [ ] **Smart Title Splitter:**
    -   Modify `_enrich_logic`.
    -   Implement logic to check `PSD_Nazev_A` length.
    -   If > 20 chars, split and move remainder to `PSD_Nazev_B`.
- [ ] **Subtitle Visibility:**
    -   Add logic to determine `PSD_Vis_Nazev_B` (new column? or reuse mechanism?).
    -   Current `HEADERS` don't have `PSD_Vis_Nazev_B`.
    -   We can add it, or just pass empty string to `PSD_Nazev_B` and rely on builder to hide if empty?
    -   User explicitly said "HIDE the subtitle layer".
    -   We should add `PSD_Vis_Nazev_B` column to Excel (index 13?) or just handle it in JSON generation (if text empty -> visibility false).
    -   **Decision:** In `_write_page_json`, if `nazev_XXB` is empty string, add `visibility: { "nazev_XXB": false }` to the action.

## Phase 2: Builder Script (`scripts/builder.jsx`)
- [ ] **A4 Group Offset:**
    -   In `processA4Groups`, after `duplicateLayerAM`, calculate offset.
    -   Use `translateLayerAM` to move the new group down.
    -   Need to determine offset amount (fixed or dynamic). Fixed `300px` might be a good start, or measure group height? Measuring is safer.
- [ ] **Image Layouting:**
    -   Update `replaceProductImageAM`.
    -   When placing images below group:
        -   Resize to 500x500px.
        -   Calculate `Group Bounds`.
        -   Place Image 1 at `Group.Right + Padding`.
        -   Place Image 2 at `Image 1.Right + Padding`.
- [ ] **Subtitle Visibility:**
    -   Ensure `updateTextLayerAM` or general visibility loop handles `nazev_XXB` hiding if flagged in JSON.

## Phase 3: Verification
- [ ] Test on A4 page.
- [ ] Verify titles split correctly.
- [ ] Verify subtitles hide if empty.
- [ ] Verify A4 groups don't overlap.
- [ ] Verify images are 500px and positioned to the right.
