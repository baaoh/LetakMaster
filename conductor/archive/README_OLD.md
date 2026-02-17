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
*   **Python:** Version 3.10 or higher
*   **Node.js:** Version 18 or higher (for frontend)
*   **Adobe Photoshop:** CC 2024 or newer

## 📦 Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/baaoh/LetakMaster.git
    cd LetakMaster
    ```

2.  **Install Dependencies**
    Double-click `install.bat` or run it from the terminal:
    ```cmd
    install.bat
    ```
    This will install required Python packages and Node.js modules for the frontend.

## ▶️ Usage

### Quick Start
The easiest way to start the application is using the provided batch script:
```cmd
start_servers.bat
```
*   **Option [1] (Recommended):** Launches both servers in the background (hidden). No extra terminal windows will pop up. The browser will open automatically.
*   **Auto-Reload:** The backend runs with `--reload` enabled, meaning any code changes to the Python logic will apply immediately without restarting the script.

### Manual Workflow

#### 1. Data Ingestion
1.  Open the web dashboard (usually `http://localhost:8000` or `http://localhost:5173`).
2.  Go to the **Data Input** tab.
3.  Select your master Excel file.
4.  The system will ingest the data and create a new "State".

#### 2. Allocation & Build Plan
1.  The system calculates the layout for every page using the **Enrichment** process. This writes PSD group keys (e.g., `Product_01`) to column **AM** (`PSD_Group`) in Excel.
2.  Generate a **Build Plan** for a specific page. This creates a JSON file in the `workspaces/build_plans` folder.

#### 3. Photoshop Automation
1.  Open your target PSD template in Adobe Photoshop.
2.  Run `scripts/run_autogen.jsx` or use the standard `File > Scripts > Browse...` to select `scripts/builder.jsx`.
3.  The script will read the JSON and automatically populate the document.

## 🌟 Advanced Features

### Manual Grouping Override (A4 Pages)
For A4/Unstructured pages, the system uses a clustering algorithm to group products automatically. You can override this directly in Excel:
1.  **Locate Column AM (`PSD_Group`):** Find the rows you want to group together.
2.  **Enter a Manual Key:** Type a custom key like `G1`, `G2`, or `GroupA` for all items in that group.
    *   *Constraint:* The key must contain at least one letter (e.g., `G1` is manual, `01` might be overwritten).
3.  **Run Enrichment:** Re-run the "Enrich Excel" process.
4.  **Result:** The script will respect your manual keys, aggregate the data for those rows into a single `A4_Grp_G1`, and skip automatic clustering for those specific items.

### Grouping Persistence (Column AL)
*   **PSD_Status (Column AL):** When a manual group is detected or created, the script writes `MANUAL` to this column.
*   **Locking:** If column AL contains `MANUAL`, the script will **strictly preserve** the grouping ID in column AM during future runs, preventing it from being overwritten by auto-clustering or getting "messed up". You can manually type `MANUAL` here to lock any group.

### Builder Script Enhancements
*   **Smart Renaming:** After generating a group in Photoshop, the script renames the layer group (e.g., `A4_Grp_G1`) to the actual product title (e.g., `Jimmyfox Candy`), making the Layers panel much more readable.
*   **Color Highlighting:** Each price tag group and its associated product images are assigned a unique color label (cycling Red, Orange, Yellow...) to visually link them together.
*   **Dynamic Stacking:** Groups are stacked vertically based strictly on their order in the JSON build plan.

### Data Handling
*   **Full Subtitles:** The system concatenates **all** variant names (e.g., flavors) into the subtitle field (`PSD_Nazev_B`), instead of truncating them with "...".
*   **Data Preservation:** The enrichment process reads existing data before writing, ensuring that skipped rows (e.g., missing page numbers) do not lose their `MANUAL` status or other data.

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
