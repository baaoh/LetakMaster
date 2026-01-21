# Implementation Plan - MVP: Core Excel-to-PSD Automation & Bridging Database

## Phase 1: Project Setup & Database Design [checkpoint: 14c237f]
- [x] Task: Initialize FastAPI project structure with TaskIQ and SQLAlchemy. [477038e]
    - [ ] Initialize git repo (already done) and create folder structure (`app/`, `tests/`, `scripts/`).
    - [ ] Configure `poetry` or `pip` requirements (`fastapi`, `sqlalchemy`, `xlwings`, `psd-tools2`, `taskiq`).
- [x] Task: Define Database Schema (The "Bridging DB"). [e48064a]
    - [ ] Create `SourceFile` model (tracker for uploaded Excel files).
    - [ ] Create `SourceData` model (stores parsed rows/cells).
    - [ ] Create `PSDFile` model.
    - [ ] Create `LayerMapping` model (FK to SourceData and PSDFile + layer_name).
    - [ ] Write tests for schema relationships.

## Phase 2: Excel Ingestion Engine
- [x] Task: Implement Excel Parsing Service. [721bbb7]
    - [ ] Create `ExcelService` class using `xlwings` (or `openpyxl` as fallback for server-side headless).
    - [ ] Implement `parse_file` method to extract data AND basic formatting (hex colors, bold).
    - [ ] Write tests: Parse sample Excel -> Verify JSON output structure.
- [ ] Task: Implement Data Ingestion API.
    - [ ] Create POST endpoint `/upload/excel`.
    - [ ] Connect parsing service to DB: Store parsed data into `SourceData`.
    - [ ] Write tests: Upload file -> Check DB records.

## Phase 3: PSD Automation Core
- [ ] Task: Implement PSD Manipulation Service.
    - [ ] Create `PSDService` using `psd-tools2`.
    - [ ] Implement `update_layers(template_path, data_mapping)`: Open PSD, find layers, update text.
    - [ ] Implement `read_layers(psd_path)`: Extract current values from a PSD.
    - [ ] Write tests: Generate dummy PSD -> Verify layer text changed.

## Phase 4: The "Bridging" Logic & Verification
- [ ] Task: Implement Integration Logic.
    - [ ] Create `BridgeService`.
    - [ ] Implement `generate_psd_from_data(row_id, template_id)`: Orchestrate DB fetch -> PSD update -> Save file -> Update `PSDFile` record.
    - [ ] Implement `verify_psd(psd_id)`: Read PSD layers -> Compare with DB -> Return diff report.
    - [ ] Implement `correct_psd(psd_id)`: Force update PSD from DB.
- [ ] Task: Background Task Configuration.
    - [ ] Wrap generation/verification methods in TaskIQ tasks.
    - [ ] Create API endpoints to trigger these tasks.

## Phase 5: GUI Implementation
- [ ] Task: Setup React Frontend.
    - [ ] Initialize React app (Vite recommended).
    - [ ] Setup API client (axios/fetch).
- [ ] Task: Build Data Explorer View.
    - [ ] Create "Excel Grid" component.
    - [ ] Implement style rendering (apply colors/bold from DB data).
- [ ] Task: Build Control Dashboard.
    - [ ] Add buttons for "Generate", "Verify", "Correct".
    - [ ] Create "Task Monitor" widget to poll/stream TaskIQ status.

## Phase 6: End-to-End Verification
- [ ] Task: Integration Testing.
    - [ ] Manual Test: Upload real Excel -> View in GUI -> Generate PSD -> Open in Photoshop to verify.
    - [ ] Manual Test: Change text in Photoshop -> Run "Verify" in GUI -> See mismatch.
    - [ ] Manual Test: Run "Correct" -> Verify PSD matches Excel again.
