# A4 Layout Refinements & Smart Content

**Status:** Done  
**Created:** 2026-01-28  
**Owner:** User / Assistant

## Overview
This track focuses on improving the visual layout and content quality of automatically generated A4 pages. Currently, generated groups stack on top of each other, images are raw-sized, and titles can overflow or have missing subtitles.

## Goals
1.  **Visual Separation:** Automatically offset generated A4 groups so they don't overlap.
2.  **Image Standardization:** Resize all placed images to 500x500px (Smart Objects) and position them cleanly to the right of the price tag.
3.  **Smart Typography:** Automatically split long titles (>20 chars) into Title/Subtitle and hide the subtitle layer if it remains empty.

## Links
- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
