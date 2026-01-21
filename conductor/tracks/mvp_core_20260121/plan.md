# Implementation Plan - MVP: Stateful Excel Sync & Bridging Database

## Phase 1: Database Refactoring & Config
- [ ] Task: Update Database Schema for State Management.
    - [ ] Add `AppConfig` (key-value storage) and `ProjectState` (json snapshots) models.
    - [ ] Create migration script or drop/recreate tables (MVP style).
    - [ ] Test: Verify new models can store/retrieve configuration and large JSON blobs.

## Phase 2: Refactor Excel Service for Local Sync
- [ ] Task: Update ExcelService for "Watch Mode".
    - [ ] Modify `parse_file` to accept a sheet name parameter.
    - [ ] Add `calculate_hash` method to quickly verify changes.
    - [ ] Test: Point to a local file, verify parsing of specific sheet.

## Phase 3: State Management Logic
- [ ] Task: Implement Sync & Diff Service.
    - [ ] `SyncService.sync_now()`: Read file -> Hash -> Save State if changed.
    - [ ] `DiffService.compare(state_a, state_b)`: Return basic added/modified/removed report.
    - [ ] API: Endpoints for `/config`, `/sync`, `/history`, `/diff/{id1}/{id2}`.

## Phase 4: GUI - Tabbed Dashboard & Config
- [ ] Task: Implement Tabbed Layout.
    - [ ] Create `MainLayout` with Bootstrap Tabs.
    - [ ] Create `DataInputTab` component.
- [ ] Task: Implement Configuration & Sync UI.
    - [ ] Form to set "Master Excel Path" and "Sheet Name".
    - [ ] "Sync Now" button with status indicator.
    - [ ] List of "History States" (timestamps).

## Phase 5: GUI - Data Visualization & Context
- [ ] Task: Implement Data Grid & Diff View.
    - [ ] Display the JSON data of the *Active State* in a virtualized grid (if large) or simple table.
    - [ ] Visual indicator for "Current vs Live" status.
    - [ ] (Bonus) Highlight changes in the grid.

## Phase 6: Final Verification
- [ ] Task: End-to-End Test.
    - [ ] Set path -> Sync -> Edit Excel -> Sync again -> Verify new state created -> Load old state -> Verify Grid updates.