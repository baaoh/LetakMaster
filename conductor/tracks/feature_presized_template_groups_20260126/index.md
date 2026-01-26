# Feature: Pre-sized Template Groups

## Context
The user has introduced new Photoshop template groups to handle "Hero" items (2-slot and 4-slot) more effectively.
- **Suffix `_K`**: Used for 2-slot items (Hero 2). Group: `Product_XX_K`.
- **Suffix `_EX`**: Used for 4-slot items (Hero 4). Group: `Product_XX_EX`.

## Goal
Update the `Enrichment` (Calculate Layouts) process to automatically detect the product size (Hero value) and append the correct suffix to the `PSD_Group` identifier in the Excel `PSD_Allocation` column (AM).

## Scope
1.  **Backend (`app/automation.py`)**: Modify `_enrich_logic` to check `res['hero']` and append suffixes.
2.  **Verification**: Ensure JSON build plans inherit these group names.

## References
- `app/automation.py`
- `app/allocation_logic.py`
