from typing import List, Dict, Optional, Tuple

class SlotAllocator:
    """
    Modular layout engine that solves the 2D bin packing problem (1x1, 1x2, 2x2).
    """
    def __init__(self, rows: int = 4, cols: int = 4):
        self.rows = rows
        self.cols = cols
        self.grid = [[True for _ in range(cols)] for _ in range(rows)]
        self.allocations = []

    def allocate(self, items: List[Dict]) -> List[Dict]:
        """
        Input: [{'id': str, 'hero': int}, ...]
        Output: [{'item_id': str, 'hero': int, 'start_slot': int, 'covered_slots': List[int]}, ...]
        """
        # Strategy 1: Attempt strict original order (Preserves visual sequence)
        try:
            return self._run_allocation(items)
        except ValueError:
            # Strategy 2: Rocks then Sand (Large items anchor to relative positions)
            try:
                return self._run_weighted_allocation(items)
            except ValueError:
                # Strategy 3: Sorted Size Descending (Guaranteed fit if math allows)
                sorted_items = sorted(items, key=lambda x: x.get('hero', 1), reverse=True)
                return self._run_allocation(sorted_items)

    def _run_allocation(self, items: List[Dict]) -> List[Dict]:
        self.grid = [[True for _ in range(self.cols)] for _ in range(self.rows)]
        results = []
        for item in items:
            hero = item.get('hero', 1)
            w, h = self._hero_to_dims(hero)
            pos = self._find_free_slot(w, h)
            if pos:
                r, c = pos
                used = self._mark_occupied(r, c, w, h)
                results.append({
                    'item_id': item['id'],
                    'hero': hero,
                    'start_slot': used[0],
                    'covered_slots': used
                })
            else:
                raise ValueError(f"Could not fit item {item['id']}")
        return results

    def _run_weighted_allocation(self, items: List[Dict]) -> List[Dict]:
        self.grid = [[True for _ in range(self.cols)] for _ in range(self.rows)]
        results = []
        rocks = [i for i in items if i.get('hero', 1) > 1]
        sand = [i for i in items if i.get('hero', 1) == 1]
        
        # Place Rocks first near their relative intended positions
        for r_item in rocks:
            hero = r_item['hero']
            w, h = self._hero_to_dims(hero)
            idx = items.index(r_item)
            ideal_slot = int((idx / len(items)) * (self.rows * self.cols))
            pos = self._find_nearest_slot(ideal_slot, w, h)
            if pos:
                r, c = pos
                used = self._mark_occupied(r, c, w, h)
                results.append({'item_id': r_item['id'], 'hero': hero, 'start_slot': used[0], 'covered_slots': used})
            else:
                raise ValueError(f"Could not fit Rock {r_item['id']}")

        # Fill gaps with Sand
        for s_item in sand:
            pos = self._find_free_slot(1, 1)
            if pos:
                r, c = pos
                used = self._mark_occupied(r, c, 1, 1)
                results.append({'item_id': s_item['id'], 'hero': 1, 'start_slot': used[0], 'covered_slots': used})
        return results

    def _hero_to_dims(self, hero: int) -> Tuple[int, int]:
        if hero == 2: return (1, 2)
        if hero == 4: return (2, 2)
        return (1, 1)

    def _find_free_slot(self, w: int, h: int) -> Optional[Tuple[int, int]]:
        for r in range(self.rows - h + 1):
            for c in range(self.cols - w + 1):
                if self._check_free(r, c, w, h):
                    return (r, c)
        return None

    def _check_free(self, r: int, c: int, w: int, h: int) -> bool:
        for i in range(r, r + h):
            for j in range(c, c + w):
                if not self.grid[i][j]: return False
        return True

    def _mark_occupied(self, r: int, c: int, w: int, h: int) -> List[int]:
        used = []
        for i in range(r, r + h):
            for j in range(c, c + w):
                self.grid[i][j] = False
                used.append((i * self.cols) + j + 1)
        return used

    def _find_nearest_slot(self, target_idx: int, w: int, h: int) -> Optional[Tuple[int, int]]:
        t_r, t_c = target_idx // self.cols, target_idx % self.cols
        candidates = []
        for r in range(self.rows - h + 1):
            for c in range(self.cols - w + 1):
                dist = abs(r - t_r) + abs(c - t_c)
                candidates.append((dist, r, c))
        candidates.sort(key=lambda x: x[0])
        for _, r, c in candidates:
            if self._check_free(r, c, w, h): return (r, c)
        return None
