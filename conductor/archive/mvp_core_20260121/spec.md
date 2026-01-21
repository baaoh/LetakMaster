# Specification: MVP Stateful Excel Sync & Bridging Database

## Overview
This track builds the core "Bridging Database" engine but pivots from a file-upload model to a **Stateful Synchronization** model. The system watches a specific, administrator-defined Excel file path. It tracks changes to specific sheets over time, recording distinct "States". Users can browse this history, see diffs (GitHub-style), and select a specific State as their "Current Context" for design operations.

The UI will be a **Tabbed Dashboard** (Data Input, Design/Layers, Settings).

## User Stories
- **As an Admin**, I want to set a local/network path to the "Master Excel File" and specify which sheet to watch.
- **As a User**, I want to click "Sync Now" to read the current Master Excel. If changes are detected compared to the latest recorded state, a new "State" is saved to the DB with a timestamp.
- **As a User**, I want to see a history of States (e.g., "State #5 - 2026-01-21 14:00 - 15 rows changed").
- **As a User**, I want to see a visual diff between two states or between a state and the live file.
- **As a User**, I want to "Load" a specific past State so that when I generate PSDs, it uses that specific data snapshot.
- **As a User**, I want a visual indicator (Green/Red dot) showing if my loaded state matches the live Excel file.

## Technical Requirements

### 1. Database Schema Updates
- `AppConfig`: Singleton table to store `master_excel_path` and `watched_sheet_name`.
- `ProjectState`: Stores a version snapshot.
    - `id`: Int
    - `created_at`: Datetime
    - `created_by`: User (String for now)
    - `excel_hash`: Hash of the sheet content (to detect no-op syncs)
    - `data_snapshot`: JSON blob of the entire sheet data (optimized later).
- `UserSession`: Tracks which `project_state_id` is active for a user/session.

### 2. Backend Logic (Excel & Diffing)
- **ExcelService:** Refactor to `read_sheet_from_path(path, sheet_name)`.
- **DiffService:** Compare two JSON datasets and return added/removed/modified rows/cells.
- **Sync Logic:**
    1. Read Live File.
    2. Compare hash with latest `ProjectState`.
    3. If different -> Create new `ProjectState`.

### 3. Frontend (Tabbed Dashboard)
- **Framework:** React + Bootstrap Tabs.
- **Tabs:**
    1.  **Data Input:**
        -   Config form (Path, Sheet).
        -   Sync Actions.
        -   History List (Click to load).
        -   Diff Viewer (Modal or split view).
        -   Data Grid (ReadOnly, showing loaded state).
    2.  **Design (Placeholder):** Future PSD controls.
- **Status Bar:** Persistent footer/header showing "Active State: #5 (Live)" or "Active State: #3 (Outdated)".

### 4. Storage Strategy
- For the MVP, we will store the parsed data as a generic JSON blob in `ProjectState` to allow flexibility.
- We will rely on row indices or a primary key column (if defined) for diffing.