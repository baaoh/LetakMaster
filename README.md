# LetakMaster v2.0: Collaborative Retail Catalog Automation

LetakMaster is a professional automation suite built for retail production teams. It integrates **Excel product data** with **Adobe Photoshop layouts** using a "Hub and Spoke" architecture to enable seamless office-wide collaboration.

## 🌟 Key Features
- **Git-Style Data Versioning:** Track changes (price, product, hero) between syncs with a shared "Commit" history.
- **Automated Layouts:** Intelligent grid allocation (16-slot) and A4 fuzzy-match clustering.
- **Collaborative Registry:** A shared Hub tracks page status, locking, and build artifacts.
- **Portable Designer Agent:** A Windows-optimized "Agent" that drives Excel and Photoshop via a portable embedded Python environment.
- **Universal Pathing:** Seamlessly share files between Windows (Designer) and Linux (Synology Hub).

## 🏗️ Architecture
- **Hub (The Brain):** FastAPI + PostgreSQL running on a Synology NAS via Docker.
- **Agent (The Hands):** FastAPI + COM Automation running locally on Windows Designer PCs.
- **Storage:** Shared assets hosted on Synology SMB (Mapped to `L:/`).

## 🚀 Quick Start

### 1. Set up the Synology Hub
1. Open **Container Manager** on your Synology NAS.
2. Create a new **Project** and use the provided `docker-compose.yml`.
3. Set your PostgreSQL passwords in the environment variables.
4. Mount your catalog assets folder to `/shared_assets`.

### 2. Set up the Designer PC
1. Clone this repository to your Windows PC.
2. Copy the `python_embed` folder into the project root.
3. Create a `.env` file based on `.env.template`:
   ```bash
   HUB_URL=http://<SYNOLOGY_IP>:8000
   DATABASE_URL=postgresql://user:pass@<SYNOLOGY_IP>:5433/letak_master
   LETAK_ROOT_PATH=L:/
   ```
4. Run `run_agent.bat`.

## 📂 Project Structure
- `/core`: Shared business logic and database schemas.
- `/server`: Synology Hub API (Server logic).
- `/client`: Windows Automation Agent (Local automation).
- `/scripts`: Photoshop JSX scripts and automation templates.

## 🔧 Technical Requirements
- **Server:** Synology NAS with Container Manager (Docker).
- **Client:** Windows 10/11, Adobe Photoshop 2024+, Microsoft Excel.

---
© 2026 LetakMaster Production Team.
