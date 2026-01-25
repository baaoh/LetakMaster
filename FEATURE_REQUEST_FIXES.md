# Feature Request: LetakMaster Stability & UX Overhaul

## 1. Fix Excel Workspace Corruption (Critical)
**Issue:**
When generating a Workspace file (`Workspace_State_XX.xlsx`) from the Master Excel using `xlwings`, the resulting file consistently throws an XML corruption error upon opening:
`Removed Records: Named range from /xl/workbook.xml part (Workbook)`

**Current Approach (Failed):**
The Python backend attempts to iterate through `wb.names` and `sheet.names` to delete broken named ranges after copying the sheet. This has proven insufficient.

**Required Fix:**
- **Deep Clean:** Implement a robust mechanism to completely strip *all* global and sheet-level named ranges during the workspace creation process.
- **XML Validation:** Investigate if `openpyxl` (which handles XML directly) should be used for the cleaning step instead of `xlwings` (COM), as COM might be masking the underlying XML corruption during the copy operation.
- **Goal:** The workspace file must open cleanly without any recovery prompts.

## 2. Streamline Saving (Ctrl+S)
**Issue:**
Users currently have to perform "Save As" after running layouts. The workspace file should be a standard, writable `.xlsx` file that supports simple saving.

**Required Fix:**
- **File Permissions:** Ensure the generated workspace file is not read-only and is not opened as a "Template" (which forces Save As).
- **Session Handling:** Verify that the `xlwings` instance or the Python backend releases the file handle completely after generation, allowing the user full exclusive write access in the Excel GUI.

## 3. In-Excel Automation Trigger ("Create Layouts?" Popup)
**Issue:**
Users want to trigger the "Calculate Layouts" (Enrichment) step immediately after opening the workspace in Excel, without switching back to the LetakMaster dashboard.

**Required Implementation:**
- **VBA Injection:** When generating the workspace file, inject a small VBA module (`Workbook_Open` event).
- **The Macro:**
    1.  On open, display a Yes/No message box: "Do you want to calculate layouts now?"
    2.  **If Yes:** The macro should call the LetakMaster API (`POST http://localhost:8000/system/automation/enrich`) OR trigger a Python script via `RunPython` (if `xlwings` add-in is present).
    3.  **Self-Destruct (Optional):** Ideally, the macro acts once or persists only for this session.
- **Alternative:** Create a dedicated Excel Ribbon Add-in for LetakMaster with a "Run Layouts" button, avoiding the need to inject code into every workspace file.

## 4. Fix Photoshop Script Path Injection (Automation)
**Issue:**
The "Run Builder Script" feature is supposed to automatically pass the **Images Directory** and **Build Plans Directory** to Photoshop so the user isn't prompted. Currently, the script still asks for paths.

**Technical Context:**
The backend reads `scripts/builder.jsx`, prepends path variables (`var g_injected_images_dir = "...";`), saves it as `scripts/run_autogen.jsx`, and instructs Photoshop to run it.

**Required Fix:**
- **Debug Path Injection:** Verify the exact string formatting of the injected paths. Windows paths (`C:\Foo\Bar`) often break JavaScript if not properly escaped as `C:\\Foo\\Bar` or `C:/Foo/Bar`.
- **Variable Scope:** Ensure the injected variables are in the correct scope for the `builder.jsx` logic to pick them up before falling back to prompts.
- **Execution Verification:** Confirm that Photoshop is actually executing the *generated* `run_autogen.jsx` and not the original template.

## 6. Image Replacement Diagnosis
**Issue:**
Images are not being replaced even when the script runs.

**Analysis:**
- **Extension Logic:** `builder.jsx` correctly appends extensions (`.png`, `.jpg`, etc.) if missing from the Excel data. This is NOT the cause.
- **Layer Matching:** The script strictly searches for layers named exactly "image", "obraz", "photo", or "packshot" (case-insensitive). PSD contains raster layer "obraz_##A" where ## is the group number.
- **Smart Objects:** Replacement commands (`placedLayerReplaceContents`) typically require the target layer to be a Smart Object. Raster layers may be ignored or cause errors.

**Recommendation:**
- Adapt so raster image replacement is supported

**Recommendation:**
- Add a configuration option for "Target Layer Name" (fuzzy match).
- Ensure the Photoshop template uses Smart Objects for product placeholders.

**Better Alternative (Recommended): "Place & Hide" Strategy**
Instead of replacing Smart Object contents (which risks distortion if aspect ratios differ), switch to a "Place & Align" logic:
1.  Find the placeholder layer (e.g., "Obraz_01").
2.  Calculate its geometric bounds (X, Y, Width, Height).
3.  Place the new image as a *new layer* above the placeholder.
4.  Resize the new image to fit/fill the calculated bounds (preserving aspect ratio).
5.  Align centered to the placeholder.
6.  Hide the original placeholder layer.
*This approach is more robust against different placeholder types (raster, shape, smart object) and avoids warping issues.*

## 5. General Performance
**Issue:**
The backend can feel sluggish.

**Recommendation:**
- Ensure all I/O-bound endpoints (File picking, DB operations, external API calls) are non-blocking (run in threadpool) to keep the UI responsive. (Note: Partial fix applied, needs verification).

---
**Technical Stack:**
- **Backend:** Python (FastAPI), `xlwings`, `sqlite3`
- **Frontend:** React (Vite)
- **Automation:** Adobe Photoshop Scripting (ExtendScript/JSX)
