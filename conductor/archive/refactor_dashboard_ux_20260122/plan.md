# Implementation Plan - Dashboard UX Refactor

## Phase 1: Backend - Excel Actions
- [x] Task: Implement `open_excel` endpoint. [1939210]
    - [x] Add `POST /open-excel` to `app/main.py`.
    - [x] Use `os.startfile` (Windows) or `xlwings.Book().activate()` to open the file.

## Phase 2: Frontend - Layout Engine
- [x] Task: Refactor `DataInputTab` layout. [b2b95c4]
    - [x] Introduce a Split Pane or Flexbox layout.
    - [x] Create `Sidebar` component (Config + History).
    - [x] Implement Collapse/Expand logic.

## Phase 3: Frontend - Data Grid Optimization
- [x] Task: Optimize `DataGrid`. [b2b95c4]
    - [x] Remove color/border rendering logic.
    - [x] Wrap in a scrollable container with fixed height/flex-grow.
    - [x] Add "Open Excel" button to the header.

## Phase 4: Integration
- [ ] Task: Verify functionality.
    - [ ] Check layout resizing.
    - [ ] Test "Open Excel" button.
    - [ ] Verify Data Grid scrolling.
