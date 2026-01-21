# Specification: MVP Core Excel-to-PSD Automation & Bridging Database

## Overview
This track focuses on building the core engine of the system: the "Bridging Database" that connects Excel input data with Photoshop (PSD) layers. It includes the backend logic to parse Excel files, the database schema to store this data alongside PSD metadata, and the automation scripts to generate and update PSD files. It also includes a basic GUI to visualize this data and trigger operations.

## User Stories
- **As a Data Manager**, I want to upload an Excel file and have its data (including formatting) parsed and stored in the database so that it can be used for design generation.
- **As a Graphic Designer**, I want to generate PSD files from the stored data using predefined templates, where specific columns map to specific layers.
- **As a Graphic Designer**, I want to "verify" a PSD file against the database to see if any manual changes were made or if data is out of sync.
- **As a User**, I want to view the Excel data in the web interface, preserving its original look/formatting, along with the status of generated PSDs.
- **As a User**, I want to click a button to "Correct" a PSD, forcing its layers to match the current database values.

## Technical Requirements

### 1. Bridging Database (SQLite)
- **Schema Design:**
    - `SourceData`: Stores raw product/supplier data from Excel.
    - `PSDFile`: Metadata about generated or managed PSD files (path, name, last_updated).
    - `LayerMapping`: The core "bridge". Maps a `SourceData` field (row/col) to a specific `PSDLayer` (layer name/ID) in a `PSDFile`.
- **Integrity:** Ensure cascading updates if source data changes.

### 2. Excel Ingestion (xlwings / pandas)
- Use `xlwings` or `pandas` to read Excel files.
- **Critical:** Extract not just values but relevant formatting (e.g., cell color, bold text) to display in the GUI.
- Fuzzy matching (using `fuzzywuzzy` or `difflib`) might be needed for mapping columns to layer names if they aren't exact matches.

### 3. PSD Automation (psd-tools2)
- Service to load a PSD template.
- Traverse layer hierarchy to find named layers matching the data mapping.
- Update text/content of layers.
- Save the modified PSD.

### 4. Verification Logic
- **Reverse Check:** Open a PSD, read layer content, compare with `SourceData` via `LayerMapping`.
- **Correction:** Overwrite PSD layer content with `SourceData` values.

### 5. GUI & Backend (FastAPI + React)
- **Backend:** API endpoints for file upload, data retrieval, task triggering (TaskIQ).
- **Frontend:**
    - Data Grid: Shows Excel data.
    - Formatting Support: The grid should visually mimic the Excel input (basic styles).
    - Actions: "Generate PSD", "Verify", "Correct".
    - Task Monitor: Real-time status of background jobs.
