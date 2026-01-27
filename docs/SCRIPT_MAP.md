# Project Script & Module Map

This document provides an overview of the codebase structure, specifically focusing on the Python backend logic and the Photoshop scripting integration.

## 🐍 Python Backend (`app/`)

The core logic for data processing, Excel manipulation, and automation.

| File | Purpose | Key Classes/Functions |
| :--- | :--- | :--- |
| **`main.py`** | **Entry Point.** The FastAPI application server. | `app` (FastAPI instance), Routes for triggering automation. |
| **`automation.py`** | **The Orchestrator.** Connects Excel, Logic, and Output. | `AutomationService`<br>`_enrich_logic`: Reads Excel, runs allocation/clustering.<br>`_generate_json_logic`: writes `build_page_XX.json`. |
| **`allocation_logic.py`** | **Grid Algorithm.** Places products into the 4x4 grid. | `SlotAllocator`: Handles "Tetris-like" fitting of products (Sizes 1, 2, 4) into a 16-slot grid. |
| **`clustering.py`** | **A4 Logic.** Groups products for unstructured pages. | `ProductClusterer`: Groups items by name similarity, price, and weight. Generates "Price Tag" text. |
| **`excel_service.py`** | **Excel I/O.** Handles low-level Excel reading/writing. | `ExcelService`: Wrapper around `xlwings` for safe file operations. |
| **`psd_service.py`** | **Photoshop Control.** Communicates with Photoshop. | Triggers `.jsx` scripts from Python. |
| **`bridge_service.py`** | **Data Bridge.** Database sync logic (Legacy/MVP). | `BridgeService`: Syncs Excel rows to a SQLite DB (Stateful sync). |

## 📜 Photoshop Scripts (`scripts/`)

ExtendScript (`.jsx`) files that run inside Photoshop to manipulate layers.

| File | Purpose | Key Features |
| :--- | :--- | :--- |
| **`builder.jsx`** | **The Constructor.** Builds the final PSD layout. | • Reads `build_page_XX.json`.<br>• `processA4Groups`: Duplicates/Renames "A4" template groups.<br>• `runBuild`: Fills text/images into layers.<br>• `scanLayersAM`: Fast ActionManager layer indexing. |
| **`run_autogen.jsx`** | **Trigger.** Simple entry point. | Runs the builder on the active document. |
| **`duplicate_products.jsx`**| **Helper.** Batch duplicator. | Utility to duplicate product groups (Legacy/Dev tool). |

## 🛠️ Utility & One-Off Scripts (`scripts/`)

Python scripts for specific tasks, testing, or cleanup.

| File | Purpose |
| :--- | :--- |
| **`enrich_excel.py`** | Standalone script to run the Enrichment logic without the API. |
| **`generate_build_json.py`**| Standalone script to generate JSONs from an enriched Excel. |
| **`apply_clustering.py`** | **Dev Tool.** Tests the `clustering.py` logic on a specific page and writes to Excel. |
| **`clean_a4_groups.py`** | **Cleanup.** Removes "A4_Grp_XX" markers from Excel (Undo for clustering). |
| **`check_headers.py`** | Verifies Excel header integrity. |
| **`analyze_layout.py`** | Analyzes a PSD file to reverse-engineer the structure (Dev tool). |

## 📂 Data Flow

1.  **Input:** User edits `workspaces/State_X.xlsx`.
2.  **Enrichment:** `automation.py` reads data -> `allocation_logic.py` (Grid) OR `clustering.py` (A4).
3.  **Output 1:** Writes calculated layout info back to Excel (Columns AM-AY).
4.  **Generation:** `automation.py` reads Columns AM-AY -> Generates `build_page_XX.json`.
5.  **Construction:** `builder.jsx` reads JSON -> Updates PSD Layers.
