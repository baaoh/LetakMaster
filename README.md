# LetakMaster

LetakMaster is a comprehensive automation suite designed to streamline the production of retail catalog pages (Letak) by integrating Excel product data with Adobe Photoshop layouts.

## 🚀 Key Features

*   **Excel Ingestion & Sync:** Tracks changes in master Excel files and maintains state history.
*   **Smart Slot Allocation:** Maps products to a 4x4 grid, handling variable item sizes (1x1, 1x2, 2x2).
*   **Photoshop Automation:** Generates JSON build plans to automatically populate PSD templates.
*   **Zero Install:** Comes with a portable environment; just clone and run.

## 📋 Prerequisites

*   **OS:** Windows 10/11
*   **Adobe Photoshop:** CC 2024 or newer

## 📦 Getting Started (Zero Install)

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/baaoh/LetakMaster.git
    cd LetakMaster
    ```

2.  **Run the Application**
    Double-click the launcher script:
    ```bash
    ./start_app_portable.bat
    ```
    *   This launches the backend and the user interface.
    *   Your browser will automatically open to `http://localhost:8000`.

## ▶️ Usage Workflow

### 1. Data Ingestion
*   Open the dashboard (`http://localhost:8000`).
*   In the **Data Input** tab, select your master Excel file.
*   The system will process the data and create a new project state.

### 2. Photoshop Automation
*   Open your target PSD template in Adobe Photoshop.
*   In Photoshop, go to `File > Scripts > Browse...`.
*   Select `scripts/builder.jsx`.
*   The script will populate the PSD with the latest data from the system.

## 🛠️ Developer Mode
If you want to modify the React frontend:
1.  Navigate to `/frontend`.
2.  Install Node.js 18+.
3.  Run `npm install` and `npm run dev`.
4.  Use `start_servers.bat` to run the backend in reload mode.

---
[Proprietary/Internal Use]