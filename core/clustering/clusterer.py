import re
import difflib
from typing import List, Dict, Optional

class ProductClusterer:
    """
    Modular engine that groups products by name, price, and weight similarity.
    Essential for 'Unstructured' A4 pages.
    """
    def __init__(self, brand_ignore: Optional[List[str]] = None):
        self.stop_words = set(brand_ignore or [
            "giana", "kaiser", "franz", "josef", "hame", "hamé", "nissin", 
            "vitana", "maggi", "dr.oetker", "hellmann's", "hellmanns"
        ])

    def cluster_items(self, items: List[Dict], sim_threshold: float = 0.85) -> List[List[Dict]]:
        """
        Groups items based on name similarity and price/weight tolerance.
        """
        if not items: return []
        
        # Sort items by Name to help greedy clustering
        sorted_items = sorted(items, key=lambda x: self._clean_name(x.get('name', '')).split() or [""])
        
        groups = []
        processed = set()
        
        for i, leader in enumerate(sorted_items):
            if i in processed: continue
            current_group = [leader]
            processed.add(i)
            
            for j, candidate in enumerate(sorted_items[i+1:], i+1):
                if j in processed: continue
                
                score = self._calculate_similarity(leader, candidate)
                price_match = self._check_price_tolerance(leader, candidate)
                
                if (price_match and score > 0.6) or score > sim_threshold:
                    current_group.append(candidate)
                    processed.add(j)
            
            groups.append(current_group)
        return groups

    def generate_smart_title(self, names: List[str]) -> str:
        """
        Extracts the common brand/product name shared by a group.
        """
        if not names: return ""
        if len(names) == 1: return names[0]
        
        # Use SequenceMatcher to find the longest common block across first two
        matcher = difflib.SequenceMatcher(None, names[0], names[1])
        match = matcher.find_longest_match(0, len(names[0]), 0, len(names[1]))
        if match.size > 3:
            candidate = names[0][match.a : match.a + match.size].strip(" -,.").title()
            return candidate
            
        return names[0].split()[0].title() # Fallback to first word

    def _clean_name(self, text: str) -> str:
        if not text: return ""
        cleaned = text.lower()
        # Remove weights (e.g., 100g, 1.5l) to focus on product name
        cleaned = re.sub(r'\d+(?:[.,]\d+)?\s*(?:g|ml|kg|l|ks)\b', '', cleaned)
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        return " ".join(cleaned.split())

    def _calculate_similarity(self, item1: Dict, item2: Dict) -> float:
        name1, name2 = self._clean_name(item1.get('name', '')), self._clean_name(item2.get('name', ''))
        return difflib.SequenceMatcher(None, name1, name2).ratio()

    def _check_price_tolerance(self, item1: Dict, item2: Dict, ratio: float = 1.6) -> bool:
        p1, p2 = item1.get('price', 0.0), item2.get('price', 0.0)
        if p1 == 0 or p2 == 0: return True
        return (max(p1, p2) / min(p1, p2)) <= ratio
