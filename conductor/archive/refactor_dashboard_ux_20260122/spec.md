# Specification: Dashboard UX Refactor & Excel Integration

## Overview
Refine the main "Data Input" dashboard to be a professional command center. The data grid serves as a fast preview, while native Excel is the primary editor. The layout will be responsive with a collapsible sidebar.

## Requirements

### 1. Sidebar Improvements
-   **Constraint:** Max width ~500px.
-   **Collapsible:** Toggle button to hide/show the sidebar.
-   **Content:** Contains Configuration form and grouped History list.

### 2. Data View Improvements
-   **Performance:** Remove cell formatting (background colors/borders) for speed.
-   **Layout:**
    -   Sticky headers.
    -   Independent scrollable container (flex-grow) so the page body doesn't scroll.
-   **Actions:**
    -   **"Open Master Excel"**: Button to launch the current file (via backend `start` command).

### 3. Backend Support
-   **Endpoint:** `POST /open-excel` to trigger `os.startfile` (or xlwings activate) on the server.

## UX Design
-   **Flex Layout:** Sidebar (Fixed) | Main Content (Flex).
-   **Main Content:** Toolbar (Actions) + Data Grid (Fill remaining).
