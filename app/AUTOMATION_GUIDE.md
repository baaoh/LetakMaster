# LetakMaster Automation Guide

This guide describes the complete workflow for automating flyer production using Excel data and Adobe Photoshop.

## 1. System Overview

The system consists of three stages:
1.  **Data Enrichment (Excel):** Calculates layout, parses text, and sets visibility rules directly in the Excel file.
2.  **Plan Generation (Python):** Extracts the enriched data into machine-readable JSON plans (one per page).
3.  **Assembly (Photoshop):** A JSX script executes the plans, updating text, resizing layout blocks, and handling visibility.

## 2. Usage Instructions

### Step 1: Enrichment
Run this script whenever the source data (Columns A-W) changes.
```bash
python_embed\python.exe scripts/enrich_excel.py
```
*   **Input:** `Copy of letak prodejna 2026 NEW FINAL.xls`
*   **Output:** Adds/Updates columns **AM-AY** in `Work_Letak_2026_v2.xls`.
*   **Columns Created:**
    *   `PSD_Group`: Allocation (e.g., `Product_01`).
    *   `PSD_Nazev_A/B`: Parsed product names.
    *   `PSD_EAN_Number`: Text-formatted EAN.
    *   `PSD_Vis_...`: Visibility flags (TRUE/FALSE) for Od, EAN, Availability.

### Step 2: Generate Build Plans
Run this to create the JSON instructions for the Photoshop builder.
```bash
# Generate for specific page (e.g., 19)
python_embed\python.exe scripts/generate_build_json.py 19
```
*   **Output:** `build_page_19.json`
*   **Content:** Contains layout actions (`hero` resizing) and data mapping (`text` + `visibility`).

### Step 3: Photoshop Assembly
**Option A: Manual Run (Designer Mode)**
1.  Open Adobe Photoshop.
2.  Open the target PSD file (e.g., `Letak W Page 19...psd`).
3.  Go to `File > Scripts > Browse...`
4.  Select `scripts/builder.jsx`.
5.  The script will:
    *   Detect "Page 19" from the filename.
    *   Load `build_page_19.json`.
    *   Execute the updates.

**Option B: Dashboard Trigger (Server Mode)**
*   The dashboard can trigger a background Python task.
*   This task uses COM (Windows) to launch Photoshop and run the script automatically.
*   *See `app/bridge_service.py` (Proposed) for implementation.*

## 3. Technical Details

### File Naming Convention
*   **Excel:** `Work_Letak_2026_v2.xls` (Working Copy).
*   **PSD:** Must contain "Page XX" or "PageXX" in the filename to auto-link with JSON.
*   **JSON:** `build_page_XX.json`.

### Logic Rules
*   **Grid:** 4x4 (16 slots).
*   **Allocation:** "Weighted Anchor" strategy (Large items anchor to their relative list position).
*   **Visibility:**
    *   `Od`: Hidden if Price column (W) is empty.
    *   `EAN Number`: Hidden if EAN Label is not "EAN:".
    *   `Availability`: Hidden if text matches default "•dostupné na všech pobočkách".

### Builder Script (`builder.jsx`)
*   **Smart Detection:** Automatically finds the correct JSON based on the open document's name.
*   **Recursive Update:** Finds layers deeply nested in groups (e.g., `Product_01 > Pricetag_01 > cena_01`).
*   **Layout Engine:**
    *   `Hero=1`: Default.
    *   `Hero=2` (Vertical): Hides the group *below* the current one.
    *   `Hero=4` (2x2): Hides the 3 groups covered (Right, Below, Below-Right).
