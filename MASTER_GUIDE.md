# LetakMaster: Collaborative Hub-Client Guide

LetakMaster is a professional, multi-user automation suite designed for high-volume retail catalog production. It connects **Excel-based product data** with **Adobe Photoshop layouts** through a centralized hub-and-spoke architecture.

---

## 🏛️ System Architecture

The system is split into two distinct tiers to enable office-wide collaboration:

### 1. The Synology Hub (The "Brain")
- **Role:** Centralized source of truth and coordination.
- **Location:** Runs on a Synology NAS (Linux/Docker).
- **Stack:** Python 3.11 (FastAPI), PostgreSQL 15.
- **Responsibility:** 
    - Managing the shared Project Registry.
    - Storing "Git-style" version history of Excel snapshots.
    - Tracking per-page "Dirty" flags and build artifacts.
    - Centralized Asset Index (NAS-wide image registry).

### 2. The Designer Agent (The "Hands")
- **Role:** Local automation and user interface.
- **Location:** Runs on individual Windows PCs (via Portable Embedded Python).
- **Stack:** Python 3.11, React (Frontend), `xlwings` (COM), Photoshop JSX.
- **Responsibility:**
    - Driving Excel and Photoshop via local COM automation.
    - Syncing local work to the Hub.
    - Performing "Deep Clean" on Excel files to prevent corruption.

---

## 🚀 The Collaborative Pipeline

### 1. Git-Style Sync & Commits
- **The Commit:** When a user syncs the Master Excel, the system creates a `ProjectState`.
- **Granular Diffing:** Instead of a simple copy, the Hub calculates exactly which cells changed (Price, Hero status, etc.).
- **Shared History:** All users see a "GitHub-style" timeline of changes, allowing the team to know exactly *why* a page needs a rebuild.
- **Dirty Flags:** If the Hub detects a data change for Page 10, it marks the page as "Dirty," notifying designers that the layout is outdated.

### 2. Universal Path Management
To allow Synology (Linux) and Designers (Windows) to share files, the system uses a **Root-Relative** path strategy:
- **DB Record:** `Archives/2026-08/state_5.xlsx`
- **Windows Mapping:** Maps `L:/LetakMaster_Assets/` + Relative Path.
- **Linux Mapping:** Maps `/volume1/LetakMaster_Assets/` + Relative Path.

### 3. Layout Enrichment & Automation
- **Grid Allocation:** Resolves 1x1, 1x2, and 2x2 product placements on a 4x4 grid.
- **A4 Clustering:** Automatically groups unstructured products by name similarity (>85% fuzzy match) and weight/price tolerance.
- **Photoshop Builder:** Generates layouts using a "Place & Align" strategy, supporting multiple images per product and smart visibility rules.

---

## 🛠️ Configuration & Deployment

### Synology Hub (Server)
Deploy using the provided `docker-compose.yml` in **Container Manager**.
- **Port 8000:** The Hub API.
- **Port 5433:** The PostgreSQL database.
- **Volume:** Mount your NAS shared folder to `/shared_assets`.

### Designer PC (Client)
Run using the portable `run_agent.bat`.
- **`.env` Configuration:**
    - `HUB_URL`: URL of the Synology Hub.
    - `LETAK_ROOT_PATH`: Local drive letter for the NAS (e.g., `L:/`).
    - `DATABASE_URL`: Connection string for the shared Postgres DB.

---

## 🔧 Core Modules (Granular Structure)
- `core/`: Shared library (Database Models, Path Translator, Tetris Logic).
- `server/`: The Hub API and Sync Coordinator.
- `client/`: The Windows Automation Agent.
- `scripts/`: Photoshop JSX templates and VBA triggers.
- `python_embed/`: The portable Windows Python runtime.

---

## 📂 Legacy Documentation
The following documents refer to the old "Single User" model and are archived in `conductor/archive/`:
- `README_OLD.md`
- `ALLOCATION.md`
- `AUTOMATION_GUIDE.md`
- `BUILD_INSTRUCTIONS.md`
