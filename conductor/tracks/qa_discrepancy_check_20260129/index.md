# QA & Discrepancy Check

**Status:** Active  
**Created:** 2026-01-29  
**Owner:** User / Assistant

## Overview
A Quality Assurance tool to verify that the content of generated Photoshop files (text, prices, EANs) matches the *current* state of the Master Excel file. This safeguards against manual edits in Photoshop or updates to the Excel file that occurred after the initial build.

## Goals
1.  **Extract:** Accurately read text content and visibility states from active PSD layers.
2.  **Compare:** Match PSD groups (e.g., `Product_01`) to Excel rows and flag differences in Name, Price, or Availability.
3.  **Report:** Present a clear "Pass/Fail" report to QA staff.

## Links
- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
