# LetakMaster Development State
**Date:** 2026-01-23
**Status:** Alpha v1 Feature Freeze - Packaging & Refinement
**Next Track:** Feature: Advanced User Management & Reporting

## System Overview
LetakMaster is a **Watch-Mode Sidecar** for Excel-based catalog production. It monitors a Master Excel file, versions it into a local SQLite database, and creates safe "Workspaces" for users to edit specific states without conflicts. It now features a robust "Click-to-Build" automation pipeline for Adobe Photoshop.

### Key Accomplishments
1.  **Stateful Sync Engine:**
    -   **Watch Mode:** Tracks a specific file path and sheet.
    -   **High-Fidelity Archiving:** Uses `xlwings` to copy the *exact* source sheet (preserving formatting/images) into `archive_files/`.
    -   **Metadata Tracking:** Analyzes page layouts (Grid16, Grid8, A4) during sync and stores them in `ProjectState.page_metadata_json`.
    -   **Decryption:** Handles password-protected legacy `.xls` files via `msoffcrypto-tool`.

2.  **Automation Pipeline (Decoupled):**
    -   **Service:** `app/automation.py` centralizes all logic (replacing standalone scripts).
    -   **Step 1: Calculate Layouts (Enrichment):** Attaches to the *active* Excel workbook, runs the `SlotAllocator` (supporting 4x4 Grid and special 4x2 Grid for Page 1), and writes mapping data to Columns AM-AY. Skips "A4" pages (Hero=0).
    -   **Step 2: Export Build Plans:** Generates structured JSON files for Photoshop, saving them to timestamped folders in `workspaces/build_plans/`. Maps Excel columns to PSD layer names.

3.  **Photoshop Builder (`builder.jsx`):**
    -   **Smart Execution:** Reads generated JSON plans.
    -   **Image Replacement:** Prompts user for an image directory and automatically finds/replaces Smart Objects based on filenames in Column AV.
    -   **Layout Management:** Toggles visibility of product groups and handles 1x2/2x2 "Hero" item overlaps.
    -   **Progress UI:** Displays a native ScriptUI progress bar during build.

4.  **Dashboard UX:**
    -   **Automation Panel:** New UI for managing the "Open Workspace -> Calculate -> Export -> Build" workflow.
    -   **Real-time Feedback:** Shows enrichment status and build plan output paths.

### Technical Stack
-   **Backend:** FastAPI (Python 3.11 embedded).
    -   `app/automation.py`: Core logic for layout calculation and JSON generation.
    -   `app/sync_service.py`: Orchestrates hashing -> parsing -> archiving -> DB saving.
-   **Frontend:** Vite + React + TypeScript.
    -   `DataInputTab.tsx`: Updated to support the decoupled automation workflow.
-   **Database:** SQLite with WAL mode.
    -   Schema updated to include `page_metadata_json`.

## Current Focus
-   **Packaging:** Creating a standalone "LetakMaster_Alpha_v1" distribution (Python Embed + Compiled Frontend).
-   **Refinement:** Handling edge cases (Page 1 geometry, A4 pages).

## Notes for Next Agent
-   **Environment:** Windows-only (COM dependency). Use `start_servers.bat` for dev.
-   **Database:** Schema changes (metadata column) require a fresh DB or migration if reusing old data.
-   **Excel:** Automation attaches to the *Active* workbook (`xw.books.active`) for zero-friction user experience.
-   **Photoshop:** `builder.jsx` is the source of truth for layer manipulation.
