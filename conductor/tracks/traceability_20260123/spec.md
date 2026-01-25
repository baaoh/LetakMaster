# Feature Specification: Product Traceability & PSD Preview

## 1. Goal
Enable users to track which products appeared on which pages across historical versions of the catalog and view visual previews of those pages.

## 2. User Stories
- **Supplier Query:** "I need to find all instances of 'Coca Cola' from last month's catalog."
- **Visual Verification:** "Show me the image of Page 10 where 'Coca Cola' was placed."
- **Audit:** "Which products were on Page 5 in the Grid16 layout vs the A4 layout?"

## 3. Data Model Requirements
### 3.1 `ProductIndex`
A normalized table derived from `ProjectState.data_snapshot_json` for fast querying.
- `id`: PK
- `project_state_id`: FK
- `page_number`: Integer
- `product_name`: String (Column C/D)
- `supplier_name`: String (Column J: "Název dodavatele")
- `ean`: String
- `psd_slot`: String (e.g., "Product_01")

### 3.2 `PageAsset`
Tracks the visual assets (PSD/PNG) associated with a page.
- `page_number`: Integer
- `psd_path`: String (Path to source PSD, discovered via Scan)
- `preview_path`: String (Path to generated PNG)
- `last_rendered`: Timestamp

## 4. Backend Logic
### 4.1 Indexing
- Triggered after `SyncService.sync_now()` saves a new `ProjectState`.
- Parsing logic iterates `data_snapshot_json`:
    - **Supplier:** Extract from Column J (Index 9).
    - **Page:** Column V (Index 21).
    - **Product:** Column D (Index 3).
    - Insert into `ProductIndex`.

### 4.2 PSD Scanning & Rendering
- **Scan:** `PSDService.scan_directory(root_path)` looks for `*Page {N}*.psd`.
- **Render:** Use `psd-tools` to composite the image.
- **Save:** `frontend_static/previews/page_{N}.png`.
- **Association:** Store path in `PageAsset`.

## 5. API Endpoints
- `GET /products/search?q={query}`: Returns list (Date, Page, Product, Supplier).
- `GET /suppliers`: List unique suppliers.

## 6. Frontend
- **New Tab:** "Traceability"
- **Search Bar:** Input text.
- **Results Table:** Date | Page | Product | Action (View Page)
- **Preview Modal:** Shows the PNG of the page.
