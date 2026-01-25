# LetakMaster

LetakMaster is a comprehensive automation suite designed to streamline the production of retail catalog pages (Letak) by integrating Excel product data with Adobe Photoshop layouts. It serves as a bridge between data managers and graphic designers, ensuring data integrity, automating tedious layout tasks, and providing a history of changes.

## 🚀 Features

*   **Excel Ingestion & Sync:** Automatically reads and parses master Excel files (including password-protected ones). Tracks changes over time and maintains a history of "states".
*   **Smart Slot Allocation:** Uses a "Tetris-like" algorithm (`SlotAllocator`) to map products to grid slots on a page, handling variable item sizes (1x1, 1x2, 2x2 "Hero" items).
*   **Photoshop Automation:** Generates JSON build plans that drive Adobe Photoshop scripts (`.jsx`) to automatically populate text layers, prices, and product images, handling complex visibility logic for overlapping groups.
*   **Traceability:** Verifies the final visual output (PSD) against the original source data to ensure accuracy.
*   **Dashboard UI:** A modern React-based frontend to manage workspaces, view product data, and trigger automation tasks.
*   **Background Processing:** Handles resource-intensive tasks asynchronously.

## 🛠️ Tech Stack

*   **Backend:** Python 3.x, FastAPI, SQLAlchemy (SQLite), Pandas
*   **Frontend:** React, TypeScript, Vite, Tailwind CSS
*   **Automation:** Adobe Photoshop ExtendScript (`.jsx`), `psd-tools`

## 📋 Prerequisites

*   **OS:** Windows 10/11 (Required for Photoshop COM automation)
*   **Adobe Photoshop:** CC 2024 or newer
*   *(Optional - For Developers only)* **Node.js:** Version 18+ (if you want to modify the frontend code)

## 📦 Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/baaoh/LetakMaster.git
    cd LetakMaster
    ```

2.  **That's it!**
    This project comes with a **Portable Python Environment** (`python_embed/`) and pre-built frontend assets. You do **not** need to install Python, Node.js, or create any virtual environments to use the application.

## ▶️ Usage

### Quick Start (User Mode)
Double-click the portable launcher script:
```bash
./start_app_portable.bat
```
This will:
1.  Launch the Python backend (using the embedded runtime).
2.  Serve the pre-built user interface.
3.  Automatically open your web browser to `http://localhost:8000`.

### Developer Mode (Optional)
If you want to modify the React frontend code:
1.  Install Node.js.
2.  Run `cd frontend && npm install`.
3.  Use `./start_servers.bat` to run the backend and the Vite dev server with hot-reloading.

### Manual Workflow

#### 1. Data Ingestion
1.  Open the web dashboard (`http://localhost:8000`).
2.  Go to the **Data Input** tab.
3.  Select your master Excel file (e.g., `Copy of letak prodejna 2026 NEW FINAL.xls`).
4.  The system will ingest the data and create a new "State".

#### 2. Allocation & Build Plan
1.  The system calculates the layout for every page using the **Enrichment** process. This writes a `PSD_Allocation` value (e.g., `P25_01A`) to the Excel data.
2.  Generate a **Build Plan** for a specific page (e.g., Page 25). This creates a JSON file containing all the text and logic needed for Photoshop.
    ```bash
    # Example manual command using embedded python
    python_embed\python.exe scripts/generate_build_json.py 25
    ```

#### 3. Photoshop Automation
1.  Open your target PSD template in Adobe Photoshop (e.g., `Letak W Page 10...`).
2.  In Photoshop, go to `File > Scripts > Browse...`.
3.  Select `scripts/builder.jsx`.
4.  The script will read the generated JSON and populate the active document, updating names, prices, and handling layout visibility.

## 🧩 Architecture Logic

### Slot Allocation
The core logic resides in `app/allocation_logic.py`. It maps a flat list of products to a 4x4 grid (or similar) on a catalog page.
*   **Standard Items:** 1 slot.
*   **Hero Items:** Can take 2 horizontal slots, 2 vertical slots, or a 2x2 box.
*   **Logic:** The allocator respects the sort order from Excel but will "flow" items around Hero products to minimize gaps.

### Photoshop Layers
The Photoshop templates must follow a specific naming convention for the automation to work:
*   Groups named `Product_01`, `Product_02`, etc.
*   Text layers inside named `nazev_XX` (Name), `cena_XX` (Price), etc.
*   The `builder.jsx` script controls the visibility of these groups based on the `PSD_Allocation` data.

## 🤝 Contributing
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

## 📄 License
[Proprietary/Internal Use]
