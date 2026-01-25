# Specification: LetakMaster Stability & UX Overhaul

## 1. Excel Workspace Corruption Fix
**Problem:** `Workspace_State_XX.xlsx` files generated via `xlwings` contain corrupted XML related to named ranges (`/xl/workbook.xml`), causing Excel to repair the file on open.
**Requirement:**
- The system must strip **ALL** named ranges (global and sheet-level) during the workspace creation process.
- The resulting file must open in Excel without any error or repair dialogs.
- Validation: Consider using `openpyxl` for the cleaning step if `xlwings` COM automation is the source of corruption or hides it.

## 2. Streamline "Save" Workflow
**Problem:** Generated workspaces often open in a state that requires "Save As" (e.g., Read-Only or Template mode).
**Requirement:**
- The generated file must be a standard `.xlsx`.
- The file handle must be fully released by the backend so the user has exclusive write access.
- `Ctrl+S` should work immediately without prompting for a filename/location.

## 3. In-Excel Automation Trigger
**Problem:** Users have to switch back to the web dashboard to trigger "Calculate Layouts" (Enrichment).
**Requirement:**
- Inject a VBA `Workbook_Open` macro into the generated workspace.
- **Behavior:**
    1.  On Open: Show Yes/No dialog: "Update Layouts?"
    2.  If Yes: Call the local API (`POST /system/automation/enrich`) or run a python script.
- **Constraint:** The macro should be unobtrusive or self-destructing if possible, or part of a standard add-in.

## 4. Photoshop Automation Path Injection
**Problem:** `builder.jsx` prompts for directories even when triggered automatically, breaking the "one-click" flow.
**Requirement:**
- The backend must inject `g_injected_images_dir` and `g_injected_build_plans_dir` variables into a temporary execution script (`run_autogen.jsx`).
- **Path Formatting:** Ensure paths are escaped correctly for JavaScript (e.g., `C:\\Path\\To\\Dir` or `C:/Path/To/Dir`).
- `builder.jsx` must prioritize these global variables over user prompts.

## 5. General Performance
**Problem:** Backend sluggishness.
**Requirement:**
- Offload I/O-heavy operations (file generation, DB access) to non-blocking threads to keep the FastAPI server responsive.
