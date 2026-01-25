# Slot Allocator & Excel Enrichment Module

This module solves the "Flyer Layout Problem": dynamically mapping a list of products (rows in Excel) to a fixed 4x4 grid (16 slots) in Photoshop, while respecting variable product sizes (Hero 1, 2, 4).

## Core Components

### 1. `SlotAllocator` (`app/allocation_logic.py`)
The engine that performs the 2D bin packing.

**Input:** List of product dictionaries:
```python
[
  {'id': 'Row_1', 'hero': 1},
  {'id': 'Row_2', 'hero': 4}, # 2x2 Block
  {'id': 'Row_3', 'hero': 2}  # 1x2 Vertical
]
```
*Note: Total `hero` sum must be exactly 16.*

**Output:** List of allocation results:
```python
[
  {'product_id': 'Row_2', 'hero': 4, 'start_slot': 1, 'covered_slots': [1,2,5,6]},
  ...
]
```

### 2. Multi-Pass Strategy
The allocator uses a fallback mechanism to handle complex layouts:

1.  **Strategy 1: Strict Order (First Fit)**
    *   Attempts to place items exactly in the order they appear in the list.
    *   Best for carefully curated pages where the user has planned the holes (e.g., Page 25).
    *   Preserves exact visual sequence.

2.  **Strategy 2: Weighted Anchor ("Rocks First")**
    *   Used if Strategy 1 fails (e.g., Page 19).
    *   Separates items into **Rocks** (Hero > 1) and **Sand** (Hero 1).
    *   **Rocks** are placed first, attempting to anchor them near their *relative position* in the original list (e.g., a big item at the end of the list tries to sit at the bottom-right).
    *   **Sand** fills the remaining gaps top-to-bottom.
    *   This ensures that big items don't "float" to the top arbitrarily (as they would with a simple Descending Sort) but stay near their intended list position.

3.  **Strategy 3: Sorted Descending (Tetris Fallback)**
    *   Last resort. Sorts largest to smallest.
    *   Guarantees a mathematical fit if one exists, but ignores list order completely.

### 3. Excel Enrichment (`scripts/enrich_excel.py`)
This script acts as the bridge between Data and Design.

*   **Reads** `Copy of letak prodejna 2026 NEW FINAL.xls`.
*   **Groups** rows by Page Number (Col V).
*   **Validates** that the sum of HERO (Col L) is exactly 16 per page.
*   **Runs** `SlotAllocator` for each valid page.
*   **Writes** the result to **Column X** (`PSD_Allocation`).
    *   Format: `Product_01`, `Product_12`, etc.
    *   This tells the future Photoshop script: *"Put this Excel row into Group Product_01"*.

## Usage for Future Agents

To apply this logic to new data or extend the project:

1.  **Run Enrichment:**
    ```bash
    python_embed\python.exe scripts/enrich_excel.py
    ```
    *Always run this after the Excel source data changes.*

2.  **Read Allocations:**
    When building the Photoshop generation script (`builder.jsx` or similar), **do not recalculate positions**. Simply read **Column X** from the Excel file.
    *   If Row 100 has `Product_01` in Column X, put Row 100's data into the `Product_01` group in PSD.
    *   If Row 100 has `Hero=4`, you must also **Hide** the groups covered by `Product_01` (which the allocator has calculated implicitly, but the builder logic needs to handle resizing `Product_01` to 2x2).

## Grid Coordinate System (4x4)
The allocator uses a 1-based Slot ID system (1-16) mapping to a 0-based Matrix (0-3, 0-3).

| | Col 1 | Col 2 | Col 3 | Col 4 |
|---|---|---|---|---|
| **Row 1** | Slot 1 | Slot 2 | Slot 3 | Slot 4 |
| **Row 2** | Slot 5 | Slot 6 | Slot 7 | Slot 8 |
| **Row 3** | Slot 9 | Slot 10 | Slot 11 | Slot 12 |
| **Row 4** | Slot 13 | Slot 14 | Slot 15 | Slot 16 |

*   **1x2 Vertical:** Occupies `Slot N` and `Slot N+4`.
*   **2x2 Box:** Occupies `Slot N`, `Slot N+1`, `Slot N+4`, `Slot N+5`.

## Future Improvements
*   **Visualizer:** A script to draw a simple ASCII or HTML map of the allocated pages to verify layout before opening Photoshop.
*   **Hero 3:** Currently only Hero 1, 2, 4 are supported. Hero 3 (1x3 or 3x1) logic can be added to `SlotAllocator` easily.
