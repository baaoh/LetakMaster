# Conductor: LetakMaster Hub-Client Index

This index manages the collaborative "Hub and Spoke" architecture of LetakMaster.

## 🧭 Project Navigation
- **[Product Definition](product.md)**: Collaborative Catalog Production.
- **[Tech Stack](tech-stack.md)**: Synology Hub (Linux/Docker) + Designer Agent (Windows).
- **[Workflow](workflow.md)**: Git-style Sync, Page Snapshots, and Shared History.
- **[Master Guide](../MASTER_GUIDE.md)**: Technical source of truth.

## 🏗️ Architectural Components
1. **The Hub (Server)**
   - Location: `/server`
   - Registry: PostgreSQL / Docker
   - Goal: Shared memory and history.

2. **The Agent (Client)**
   - Location: `/client`
   - Engine: Windows Embedded Python / COM
   - Goal: Local Excel and Photoshop automation.

3. **The Shared Core**
   - Location: `/core`
   - Goal: Universal logic (Tetris, Diffs, Path Management).

## 🚀 Active Tracks
- **Track 1: Infrastructure Migration** (Current Focus)
  - Setting up Synology Hub (PostgreSQL).
  - Porting local logic to modular `core/` library.
  - Implementing Git-style diffing.

---
*See [Archive](./archive/) for legacy Single-User documentation.*
