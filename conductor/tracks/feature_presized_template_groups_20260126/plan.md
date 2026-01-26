# Implementation Plan - Pre-sized Template Groups

## Phase 1: Logic Implementation
- [x] Task: Create a reproduction test case (or unit test) to simulate the enrichment mapping logic.
- [x] Task: Modify `app/automation.py` `_enrich_logic` to append `_K` for Hero 2 and `_EX` for Hero 4.

## Phase 2: Verification
- [x] Task: Verify the unit test produces `Product_XX_K` and `Product_XX_EX` strings.
- [x] Task: Update `builder.jsx` to strictly hide standard `Product_XX` group when `Product_XX_K/EX` is active.
- [x] Task: Fix builder.jsx visibility logic to handle layer suffixes (_K/_EX) for EAN and Availability layers.
- [x] Task: (Manual) User to verify `builder.jsx` picks up the new group names in Photoshop. (Verified: Works, with AM optimization)
