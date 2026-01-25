# Implementation Plan - Stability & UX Overhaul

## Phase 1: Excel Core Stability
- [x] Task: Reproduce XML corruption issue with current `xlwings` copy logic.
- [x] Task: Implement `openpyxl` based cleaning utility to strip all named ranges from the generated `.xlsx`.
- [x] Task: Verify workspace generation no longer triggers "Repaired Records" on open.
- [x] Task: Ensure generated file permissions allow direct `Ctrl+S` (release file handles).

## Phase 2: Excel <-> Backend Bridge
- [ ] Task: Create a VBA template for `Workbook_Open` trigger.
- [x] Task: Implement `enrich_active_book` entry point in `automation.py`.
- [ ] Task: Implement VBA injection logic during workspace generation.

## Phase 3: Photoshop Automation
- [x] Task: Audit `psd_service.py` (or `main.py`) for script generation logic.
- [x] Task: Fix path escaping for `g_injected_images_dir` and `g_injected_build_plans_dir`.
- [x] Task: Verify `builder.jsx` correctly reads these injected variables.
- [x] Task: Test end-to-end "Run Builder" flow without prompts.

## Phase 4: Performance & Cleanup
- [x] Task: Audit `main.py` endpoints for blocking file I/O.
- [x] Task: Refactor critical paths to use `await run_in_threadpool`.
