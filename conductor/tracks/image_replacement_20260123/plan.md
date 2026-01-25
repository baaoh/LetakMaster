# Implementation Plan - Image Replacement

## Phase 1: Script Refactoring
- [x] Task: Create a standalone test script `scripts/test_place_image.jsx` to prototype the "Place & Hide" logic on a single active document.
- [x] Task: Implement `getLayerBounds(layer)` helper.
- [x] Task: Implement `fitLayerToBounds(layer, bounds)` helper (maintain aspect ratio).
- [x] Task: Implement `placeAndAlign(doc, group, placeholderName, imageFile)` function.

## Phase 2: Integration
- [x] Task: Integrate the new logic into `scripts/builder.jsx`.
- [x] Task: Update `replaceProductImage` to use the new strategy instead of `replaceSmartObjectContents`.
- [x] Task: Enhance layer finder to look for `image`, `obraz`, `photo` *containing* the suffix or just generic names.

## Phase 3: Verification
- [ ] Task: Verify with "Raster" placeholder.
- [ ] Task: Verify with "Smart Object" placeholder.
- [ ] Task: Verify with different aspect ratio images.
