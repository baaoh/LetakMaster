# LetakMaster: Comprehensive Master Guide

LetakMaster is a professional automation suite designed to bridge the gap between **Excel-based product data** and **Adobe Photoshop retail layouts**. It provides a robust pipeline for data ingestion, layout calculation (Grid & A4), automated building, and QA traceability.

---

## 🏗️ System Architecture

### Tech Stack
- **Backend:** Python 3.10+ (FastAPI, SQLAlchemy, Pandas)
- **Frontend:** React + TypeScript (Vite, Tailwind CSS, React-Bootstrap)
- **Automation:** Adobe Photoshop ExtendScript (JSX) via COM/IFileOpenDialog.
- **Excel Engine:** `xlwings` (COM) for high-fidelity sync, `openpyxl` (XML) for deep cleaning.
- **Database:** SQLite (WAL mode) for state versioning and traceability.

### Key Directories
- `app/`: Core backend logic (Automation, Sync, QA).
- `scripts/`: Photoshop `.jsx` scripts and VBA triggers.
- `frontend/`: React dashboard source code.
- `workspaces/`: Local user storage for states, build plans, and QA scans.
- `archive_files/`: Versioned snapshots of the master Excel.

---

## 🚀 The Automation Pipeline

### 1. Data Ingestion & Sync
- **Watch Mode:** The system monitors a Master Excel file. When changes are detected (via hash), it creates a new **State**.
- **Stateful Archiving:** Source sheets are copied into `archive_files/` with formatting and images preserved.
- **Deep Clean:** The system automatically strips named range corruption and external links to ensure stability.

### 2. Layout Enrichment (The "Brain")
LetakMaster handles two primary page types:
- **Grid Pages (16 Slots):** Uses a Tetris-like `SlotAllocator` to map products (1x1, 1x2, 2x2) to a 4x4 grid.
- **A4 / Unstructured Pages:** Uses `ProductClusterer` to group similar products by name, weight, and price similarity (>85% fuzzy match).
- **Manual Override:** Users can type `MANUAL` in column **AL** or a custom key in **AM** to lock specific groupings. Enrichment respects these manual overrides.

### 3. Photoshop Assembly (The "Builder")
- **Dynamic JSON:** Enrichment generates a `build_page_XX.json` containing text, visibility, and image instructions.
- **Path Injection:** The backend dynamically generates `run_autogen.jsx` with safely escaped paths for images and plans.
- **Smart Building:**
    - **Place & Align:** Images are placed as new layers, resized to fit placeholders, and aligned centered.
    - **Multiple Images:** Supports multiple placeholders (A, B, C...) within a single group.
    - **Visibility Logic:** Automatically hides/shows EANs, "Od" prefixes, and availability labels based on data rules.
    - **QOL Features:** Progress bars, unique group coloring, and automatic layer renaming.

---

## 🛠️ Integrated UX Features

### In-Excel Trigger
- **VBA Popup:** Workspace files (`.xlsm`) include a `Workbook_Open` trigger that asks: *"Do you want to calculate layouts now?"*.
- **API Bridge:** This calls the LetakMaster backend directly, allowing designers to trigger enrichment without leaving Excel.

### QA & Traceability
- **Discrepancy Check:** Scans final PSDs and compares them against the Master Excel.
- **Highlighting:** Discrepancies are highlighted in **Orange** in Excel.
- **Visual Inspection:** High-fidelity previews and coordinate-mapped inspection tools in the dashboard allow quick verification.

---

## 🔧 Maintenance & Configuration

### Environment Requirements
- **OS:** Windows 10/11 (Required for COM/Photoshop automation).
- **Excel Settings:** To use the VBA trigger, enable:
  `File > Options > Trust Center > Trust Center Settings > Macro Settings > Trust access to the VBA project object model`.

### Common Fixes (2026-02-17 Update)
- **Excel Corruption:** If a workspace fails to open, ensure `openpyxl` is installed. The system now uses a "Deep Clean" pass during workspace creation to remove broken XML records.
- **Path Injection:** Script paths are now JSON-escaped. No more failures due to backslashes or quotes in folder names.
- **Saving:** Workspaces are opened with `read_only=False`. Standard Ctrl+S saving is now supported.

---

## 📂 Deprecated / Outdated Files (Archived)
The following files have been superseded by this guide and should be referenced only for historical context:
- `README.md` (Partial overlap, mostly still relevant for Quick Start)
- `DEV_NEXT_STEPS.md` (Merged into Pipeline section)
- `DEV_STATE.md` (Outdated status)
- `FEATURE_REQUEST_FIXES.md` (Implementation complete)
- `app/ALLOCATION.md` (Logic merged into Section 2)
- `app/AUTOMATION_GUIDE.md` (Merged into Section 2/3)
- `app/BUILD_INSTRUCTIONS.md` (Merged into Section 3)
