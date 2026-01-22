# Implementation Plan - Dashboard UX Refactor

## Phase 1: Backend - Excel Actions
- [ ] Task: Implement `open_excel` endpoint.
    - [ ] Add `POST /open-excel` to `app/main.py`.
    - [ ] Use `os.startfile` (Windows) or `xlwings.Book().activate()` to open the file.

## Phase 2: Frontend - Layout Engine
- [ ] Task: Refactor `DataInputTab` layout.
    - [ ] Introduce a Split Pane or Flexbox layout.
    - [ ] Create `Sidebar` component (Config + History).
    - [ ] Implement Collapse/Expand logic.

## Phase 3: Frontend - Data Grid Optimization
- [ ] Task: Optimize `DataGrid`.
    - [ ] Remove color/border rendering logic.
    - [ ] Wrap in a scrollable container with fixed height/flex-grow.
    - [ ] Add "Open Excel" button to the header.

## Phase 4: Integration
- [ ] Task: Verify functionality.
    - [ ] Check layout resizing.
    - [ ] Test "Open Excel" button.
    - [ ] Verify Data Grid scrolling.
