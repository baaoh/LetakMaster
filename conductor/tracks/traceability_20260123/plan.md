# Implementation Plan - Feature: Product Traceability & PSD Preview

## Phase 1: Database & Indexing
- [x] Task: Create `ProductIndex` model in `database.py`.
- [x] Task: Create `PageAsset` model in `database.py`.
- [x] Task: Update `SyncService` to populate `ProductIndex` after saving state.
- [x] Task: Verify indexing works for existing states (Migration script?).

## Phase 2: PSD Rendering Engine
- [x] Task: Update `PSDService` to include `render_preview(psd_path, output_path)`.
- [x] Task: Implement `PSDManager` to scan folder for `*Page XX*.psd` files and map them to Page Numbers.
- [x] Task: Create API `POST /system/render-previews` to batch process PSDs.

## Phase 3: API & Search Logic
- [x] Task: Implement `GET /products/search`.
- [x] Task: Implement `GET /pages/{page_num}/preview`.

## Phase 4: Frontend UI
- [x] Task: Create `TraceabilityTab.tsx`.
- [x] Task: Implement Search Bar and Results Table.
- [x] Task: Implement Image Preview Modal.
- [x] Task: Add Tab to `MainLayout.tsx`.

## Phase 5: Verification
- [x] Task: End-to-End Test: Sync Excel -> Index Products -> Search Product -> View Page Image.