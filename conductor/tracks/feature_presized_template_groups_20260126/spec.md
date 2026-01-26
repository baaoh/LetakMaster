# Specification - Pre-sized Template Groups

## Logic
The `PSD_Group` identifier (Column AM in Excel) is the primary key used by `builder.jsx` to locate the target LayerGroup in Photoshop.

### Rules
1.  **Standard (Hero 1):** `Product_{slot_id:02d}` (e.g., `Product_01`)
2.  **Hero 2:** `Product_{slot_id:02d}_K` (e.g., `Product_01_K`)
3.  **Hero 4:** `Product_{slot_id:02d}_EX` (e.g., `Product_01_EX`)

### Data Flow
1.  `SlotAllocator` determines the `hero` value (1, 2, or 4) and the `start_slot`.
2.  `AutomationService._enrich_logic` constructs the string.
3.  Excel Column AM is populated.
4.  `AutomationService._write_page_json` reads Column AM and writes it to `"group"` field in JSON.
5.  `builder.jsx` uses `doc.layerSets.getByName(json.group)`.
