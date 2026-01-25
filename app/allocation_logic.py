class SlotAllocator:
    def __init__(self, rows=4, cols=4):
        self.rows = rows
        self.cols = cols
        # Grid is True if free, False if occupied
        # 0-indexed internally for easier math, converted to 1-based for output
        self.grid = [[True for _ in range(cols)] for _ in range(rows)]
        self.allocations = [] # Stores (product_index, start_slot_id, used_slots_ids)

    def find_free_slot(self, width, height):
        """
        Finds the first position (r, c) where a block of width x height fits.
        Returns (r, c) or None.
        """
        for r in range(self.rows - height + 1):
            for c in range(self.cols - width + 1):
                if self.check_free(r, c, width, height):
                    return (r, c)
        return None

    def check_free(self, r, c, width, height):
        for i in range(r, r + height):
            for j in range(c, c + width):
                if not self.grid[i][j]:
                    return False
        return True

    def mark_occupied(self, r, c, width, height):
        used_slots = []
        for i in range(r, r + height):
            for j in range(c, c + width):
                self.grid[i][j] = False
                # Calculate 1-based slot ID: (Row * Cols) + Col + 1
                slot_id = (i * self.cols) + j + 1
                used_slots.append(slot_id)
        return used_slots

    def allocate(self, products):
        """
        products: list of dicts {'id': any, 'hero': int}
        Returns list of results or raises Exception if completely impossible.
        """
        import copy
        
        # Strategy 1: Strict Input Order (Best for carefully planned pages like Pg 25)
        try:
            print("Attempting Strategy 1: Strict Order...")
            return self._run_allocation(products, reverse_fill=False)
        except ValueError:
            print("Strategy 1 failed.")

        # Strategy 2: Weighted Anchor (Rocks then Sand)
        # 1. Identify "Rocks" (Hero > 1) and "Sand" (Hero 1).
        # 2. Place Rocks as close to their original relative list position as possible.
        # 3. Fill gaps with Sand.
        try:
            print("Attempting Strategy 2: Weighted Anchor (Rocks First)...")
            return self._run_weighted_allocation(products)
        except ValueError:
            print("Strategy 2 failed.")

        # Strategy 3: Sorted by Size (Tetris style - guarantees fit if math allows)
        try:
            print("Attempting Strategy 3: Sorted Size Descending...")
            sorted_products = sorted(products, key=lambda x: x['hero'], reverse=True)
            return self._run_allocation(sorted_products, reverse_fill=False)
        except ValueError:
            print("Strategy 3 failed.")
            raise Exception("Could not fit products even with sorting. Check Total Hero count.")

    def _run_allocation(self, products, reverse_fill=False):
        # Reset grid
        self.grid = [[True for _ in range(self.cols)] for _ in range(self.rows)]
        results = []
        
        # If reverse_fill, we iterate products backwards AND find slots backwards
        process_list = products[::-1] if reverse_fill else products
        
        for p in process_list:
            hero = p['hero']
            w, h = 1, 1
            if hero == 2: w, h = 1, 2
            elif hero == 4: w, h = 2, 2
            
            pos = self.find_free_slot(w, h, reverse=reverse_fill)
            
            if pos:
                r, c = pos
                used = self.mark_occupied(r, c, w, h)
                start_slot = used[0] # Always reference by Top-Left slot ID
                
                results.append({
                    'product_id': p.get('id'),
                    'hero': hero,
                    'start_slot': start_slot,
                    'covered_slots': used
                })
            else:
                if reverse_fill:
                    print(f"DEBUG: Failed to place {p.get('id')} (Hero {hero}) in Reverse Mode")
                raise ValueError(f"Could not fit Product {p.get('id')}")
        
        return results

    def _run_weighted_allocation(self, products):
        self.grid = [[True for _ in range(self.cols)] for _ in range(self.rows)]
        results = []
        
        total_items = len(products)
        rocks = []
        sand = []
        
        for i, p in enumerate(products):
            p['_original_index'] = i
            if p['hero'] > 1:
                rocks.append(p)
            else:
                sand.append(p)
        
        # 1. Place Rocks
        for r in rocks:
            hero = r['hero']
            w, h = (1, 2) if hero == 2 else (2, 2) if hero == 4 else (1, 1)
            
            # Calculate ideal slot based on list position (0.0 to 1.0)
            ratio = r['_original_index'] / total_items
            ideal_slot_idx = int(ratio * (self.rows * self.cols))
            
            # Search for nearest valid slot to ideal_slot_idx
            # We search outwards from the ideal slot
            found_pos = self._find_nearest_slot(ideal_slot_idx, w, h)
            
            if found_pos:
                row, col = found_pos
                used = self.mark_occupied(row, col, w, h)
                results.append({
                    'product_id': r.get('id'),
                    'hero': hero,
                    'start_slot': used[0],
                    'covered_slots': used
                })
            else:
                raise ValueError(f"Could not fit Rock {r.get('id')}")

        # 2. Fill Sand (in original order)
        # We just fill the first available holes top-to-bottom
        for s in sand:
            pos = self.find_free_slot(1, 1)
            if pos:
                row, col = pos
                used = self.mark_occupied(row, col, 1, 1)
                results.append({
                    'product_id': s.get('id'),
                    'hero': 1,
                    'start_slot': used[0],
                    'covered_slots': used
                })
            else:
                 raise ValueError(f"Could not fit Sand {s.get('id')}")
                 
        # Sort results by start_slot to look nice in output, 
        # but technically we should return them so the caller knows the mapping.
        # The list order in 'results' doesn't dictate layout, 'start_slot' does.
        return results

    def _find_nearest_slot(self, target_slot_idx, width, height):
        # target_slot_idx is 0..15
        # Convert to (r, c)
        
        # We search by distance from target
        # Generate all (r, c) sorted by distance to target
        
        target_r = target_slot_idx // self.cols
        target_c = target_slot_idx % self.cols
        
        candidates = []
        for r in range(self.rows - height + 1):
            for c in range(self.cols - width + 1):
                dist = abs(r - target_r) + abs(c - target_c) # Manhattan distance
                candidates.append((dist, r, c))
        
        candidates.sort(key=lambda x: x[0]) # Sort by closest distance
        
        for _, r, c in candidates:
            if self.check_free(r, c, width, height):
                return (r, c)
        
        return None

    def find_free_slot(self, width, height, reverse=False):
        # If reverse, scan from bottom-right (Rows-1 -> 0, Cols-1 -> 0)
        rows_range = range(self.rows - height + 1)
        cols_range = range(self.cols - width + 1)
        
        if reverse:
            rows_range = list(reversed(range(self.rows - height + 1)))
            cols_range = list(reversed(range(self.cols - width + 1)))
            
        for r in rows_range:
            for c in cols_range:
                if self.check_free(r, c, width, height):
                    return (r, c)
        return None

# Test with your data
if __name__ == "__main__":
    allocator = SlotAllocator()

    print("\n=== TEST CASE 1: Page 19 (12 Small, 1 Big Last) ===")
    p19 = [{'id': f"Sm_{i}", 'hero': 1} for i in range(12)]
    p19.append({'id': "Big_Last", 'hero': 4})
    
    try:
        res = allocator.allocate(p19)
        for r in res:
            print(f"{r['product_id']:<10} | Start: {r['start_slot']}")
    except Exception as e:
        print(e)

    print("\n=== TEST CASE 2: Page 25 (Mix) ===")
    # 1x Hero 2, 6x Hero 1, 2x Hero 4 (Last)
    p25 = [{'id': "V_1", 'hero': 2}]
    p25 += [{'id': f"Sm_{i}", 'hero': 1} for i in range(6)]
    p25 += [{'id': "Big_1", 'hero': 4}, {'id': "Big_2", 'hero': 4}]
    
    try:
        res = allocator.allocate(p25)
        for r in res:
            print(f"{r['product_id']:<10} | Start: {r['start_slot']}")
    except Exception as e:
        print(e)
