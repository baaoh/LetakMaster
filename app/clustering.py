import re
import difflib
from collections import Counter

class ProductClusterer:
    def __init__(self):
        # Common brands to strip for core comparison
        self.brands = ["giana", "kaiser", "franz josef", "hame", "hamé", "nissin", "vitana", "maggi"]
        
    def extract_weight_data(self, text):
        """Returns (value, unit) or (None, None)"""
        if not text: return (None, None)
        # Match number + unit
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(g|ml|kg|l|ks)\b', text, re.IGNORECASE)
        if match:
            val_str = match.group(1).replace(',', '.')
            unit = match.group(2).lower()
            try:
                return (float(val_str), unit)
            except:
                pass
        return (None, None)

    def normalize_weight(self, val, unit):
        """Converts to grams/ml for comparison"""
        if unit in ['kg', 'l']:
            return val * 1000
        return val

    def check_value_similarity(self, val1, val2, threshold_ratio=2.0):
        """
        Returns True if values are within the threshold ratio.
        e.g. threshold 2.0 allows 100g vs 200g.
        """
        if val1 == 0 or val2 == 0: return True # Missing data -> Ignore check (Permissive)
        
        ratio = val1 / val2 if val2 != 0 else 0
        if ratio < 1.0: ratio = 1.0 / ratio # Ensure ratio >= 1
        
        return ratio <= threshold_ratio

    def extract_weight(self, text):
        # Legacy helper for name cleaning
        if not text: return None
        match = re.search(r'(\d+(?:[.,]\d+)?\s*(?:g|ml|kg|l|ks))', text, re.IGNORECASE)
        if match:
            return match.group(1).lower().replace(' ', '')
        return None

    def clean_name(self, text):
        if not text:
            return ""
        cleaned = text.lower()
        
        # Remove weight
        weight = self.extract_weight(text)
        if weight:
            cleaned = cleaned.replace(weight, "")
            cleaned = re.sub(r'/\d+(?:g|ml|kg|l)', '', cleaned) # Handle slash combos
        
        # Remove special chars
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        return " ".join(cleaned.split())

    def get_core_phrase(self, text):
        cleaned = text.lower()
        for b in self.brands:
            cleaned = cleaned.replace(b, "")
        
        tokens = cleaned.split()
        if len(tokens) >= 2:
            return " ".join(tokens[:2])
        return " ".join(tokens)

    def calculate_similarity(self, name1, name2):
        c1 = self.clean_name(name1)
        c2 = self.clean_name(name2)
        
        core1 = self.get_core_phrase(name1)
        core2 = self.get_core_phrase(name2)
        
        if core1 and core2 and core1 == core2:
            return 0.95 
            
        seq = difflib.SequenceMatcher(None, c1, c2)
        return seq.ratio()

    def generate_smart_title(self, names):
        if not names: return ""
        all_tokens = [n.split() for n in names]
        total_items = len(names)
        token_counts = Counter()
        
        for tokens in all_tokens:
            seen_in_title = set()
            for t in tokens:
                clean_t = t.lower().strip(".,()")
                if clean_t not in seen_in_title:
                    token_counts[clean_t] += 1
                    seen_in_title.add(clean_t)
        
        threshold = total_items * 0.75
        common_words = {word for word, count in token_counts.items() if count >= threshold}
        
        ref_tokens = names[0].split()
        result_tokens = []
        
        for t in ref_tokens:
            clean_t = t.lower().strip(".,()")
            if clean_t in common_words:
                result_tokens.append(t)
                
        return " ".join(result_tokens)

    def generate_variants(self, items, nazev_a):
        variants = []
        common_tokens = set(nazev_a.lower().split())
        
        for item in items:
            full_tokens = item['name'].split()
            diff = []
            for t in full_tokens:
                clean_t = t.lower().strip(".,()")
                if clean_t not in common_tokens:
                    if clean_t not in self.brands:
                        diff.append(t)
            
            variant_str = " ".join(diff).strip(" -.,")
            if variant_str:
                variants.append(variant_str)
                
        unique = sorted(list(set(variants)))
        return ", ".join(unique[:3]) + (", ..." if len(unique) > 3 else "")

    def group_items(self, items):
        """
        Main clustering function.
        items: List of dicts {'id', 'name', 'price', 'weight_text'}
        """
        groups = []
        processed_ids = set()
        
        for i, item in enumerate(items):
            if item['id'] in processed_ids:
                continue
                
            current_group = [item]
            processed_ids.add(item['id'])
            
            # Parse Item 1 Data
            core1 = self.get_core_phrase(item['name']).split()[0] if self.get_core_phrase(item['name']) else ""
            
            # Try parsing weight from Column F first, then Name
            w1, u1 = self.extract_weight_data(item.get('weight_text'))
            if w1 is None: w1, u1 = self.extract_weight_data(item['name'])
            norm_w1 = self.normalize_weight(w1, u1) if w1 else 0
            
            p1 = item.get('price', 0.0)
            
            for j, other in enumerate(items):
                if other['id'] in processed_ids:
                    continue
                
                # --- VALUE CHECKS (Strictness) ---
                
                # 1. Price Check (Max 1.6x diff)
                p2 = other.get('price', 0.0)
                # If both prices exist, enforce strict check. If one is missing, allow (maybe data error).
                if p1 > 0 and p2 > 0:
                    if not self.check_value_similarity(p1, p2, threshold_ratio=1.6): 
                        continue 
                    
                # 2. Weight Check (Max 1.6x diff)
                w2, u2 = self.extract_weight_data(other.get('weight_text'))
                if w2 is None: w2, u2 = self.extract_weight_data(other['name'])
                norm_w2 = self.normalize_weight(w2, u2) if w2 else 0
                
                if norm_w1 > 0 and norm_w2 > 0:
                    # Require units to be compatible
                    if (u1 == 'ks' and u2 != 'ks') or (u1 != 'ks' and u2 == 'ks'):
                        continue
                        
                    if not self.check_value_similarity(norm_w1, norm_w2, threshold_ratio=1.6):
                        continue
                
                # --- NAME CHECKS ---
                
                score = self.calculate_similarity(item['name'], other['name'])
                core2 = self.get_core_phrase(other['name']).split()[0] if self.get_core_phrase(other['name']) else ""
                
                # Extract first word of cleaned name for Head Noun check
                clean1 = self.clean_name(item['name'])
                clean2 = self.clean_name(other['name'])
                word1 = clean1.split()[0] if clean1 else ""
                word2 = clean2.split()[0] if clean2 else ""
                
                match = False
                
                # Strict Rule: If first significant word differs (e.g. "Instantní" vs "Soba"), 
                # require extremely high similarity (0.90) to group them.
                if word1 != word2:
                    if score > 0.90:
                        match = True
                else:
                    # Standard Rules if first word matches
                    if score > 0.85:
                        match = True
                    elif score > 0.55 and core1 == core2:
                        match = True
                    
                if match:
                    current_group.append(other)
                    processed_ids.add(other['id'])
            
            groups.append(current_group)
            
        return groups