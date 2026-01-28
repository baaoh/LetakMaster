import re
import difflib
from collections import Counter

class ProductClusterer:
    def __init__(self):
        # Common brands/words to treat as "transparent" or skip in core analysis
        self.stop_words = {
            "giana", "kaiser", "franz", "josef", "hame", "hamé", "nissin", 
            "vitana", "maggi", "dr.oetker", "hellmann's", "hellmanns", 
            "instant", "instantní", "sáčková", "polévka", "hotová", "hotova"
        }
        
    def extract_weight_data(self, text):
        """Returns (value, unit) or (None, None)"""
        if not text: return (None, None)
        # Match number + unit (e.g., 100g, 1.5l, 4x100g)
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

    def check_value_similarity(self, val1, val2, threshold_ratio=1.6):
        """
        Returns True if values are within the threshold ratio.
        """
        if val1 == 0 or val2 == 0: return True # Missing data -> Permissive
        
        ratio = val1 / val2 if val2 != 0 else 0
        if ratio < 1.0: ratio = 1.0 / ratio
        
        return ratio <= threshold_ratio

    def clean_name(self, text):
        """Normalizes text for comparison (lowercase, remove weights/specials)"""
        if not text: return ""
        cleaned = text.lower()
        
        # Remove common weight patterns to focus on product name
        cleaned = re.sub(r'\d+(?:[.,]\d+)?\s*(?:g|ml|kg|l|ks)\b', '', cleaned)
        cleaned = re.sub(r'\d+x\d+', '', cleaned) # 4x100 etc
        
        # Remove special chars
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        return " ".join(cleaned.split())

    def get_tokens(self, text):
        """Returns set of significant words"""
        cleaned = self.clean_name(text)
        tokens = cleaned.split()
        return [t for t in tokens if t not in self.stop_words and len(t) > 1]

    def calculate_similarity_score(self, item1, item2):
        """
        Complex scoring logic to mimic "AI" reasoning using heuristics.
        Returns score 0.0 to 1.0
        """
        name1 = item1['name']
        name2 = item2['name']
        
        # 1. Head Noun Check (Crucial for "Shampoo" vs "Conditioner")
        tokens1 = self.get_tokens(name1)
        tokens2 = self.get_tokens(name2)
        
        if not tokens1 or not tokens2:
            # Fallback to string distance if tokens missing
            return difflib.SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

        head1 = tokens1[0]
        head2 = tokens2[0]
        
        # If the very first significant word is different, penalty.
        # e.g. "Savo" vs "Jar" -> Different.
        head_match = (head1 == head2)
        
        # 2. Token Overlap (Jaccard) - Good for variants "Chicken Soup" vs "Beef Soup"
        set1 = set(tokens1)
        set2 = set(tokens2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        jaccard = intersection / union if union > 0 else 0
        
        # 3. Sequence Match (for word order)
        seq_ratio = difflib.SequenceMatcher(None, " ".join(tokens1), " ".join(tokens2)).ratio()
        
        # Weighted Score
        score = 0.0
        
        if head_match:
            score += 0.4  # Base score for same "Type"
            score += (jaccard * 0.4) # Add overlap
            score += (seq_ratio * 0.2) # Add order
        else:
            # If heads differ, they must be VERY similar otherwise (e.g. synonyms?)
            # Usually we just penalize heavily.
            score += (jaccard * 0.5) 
            score += (seq_ratio * 0.2)
            
        return score

    def generate_smart_title(self, names):
        """
        Extracts the common prefix/tokens that represent the Group Name.
        """
        if not names: return ""
        if len(names) == 1: return names[0]
        
        # Tokenize all names
        token_lists = [self.clean_name(n).split() for n in names]
        
        # Find Longest Common Subsequence of tokens from the start
        if not token_lists: return ""
        
        common = []
        ref = token_lists[0]
        
        for i, token in enumerate(ref):
            is_in_all = True
            for other_list in token_lists[1:]:
                # Check if token exists in other list
                if token not in other_list:
                    is_in_all = False
                    break
            if is_in_all:
                common.append(token)
            else:
                # Heuristic: If we have enough common words, maybe stop?
                # For now, let's keep collecting common words even if skipped
                pass
        
        # Fallback: Just use SequenceMatcher on the raw strings to find the common block
        matcher = difflib.SequenceMatcher(None, names[0], names[1])
        match = matcher.find_longest_match(0, len(names[0]), 0, len(names[1]))
        if match.size > 3:
            candidate = names[0][match.a : match.a + match.size].strip()
            candidate = candidate.strip(" -,.")
            return candidate.title()
            
        if common:
            return " ".join(common).title()
            
        return names[0]

    def generate_variants(self, items, group_title):
        """
        Extracts the 'variable' part of the names as the subtext.
        """
        variants = []
        title_lower = group_title.lower()
        
        for item in items:
            name = item['name']
            name_lower = name.lower()
            
            # Simple subtraction
            # We remove the group title tokens from the name
            title_tokens = title_lower.split()
            name_tokens = name_lower.split()
            
            diff_tokens = [t for t in name_tokens if t not in title_tokens]
            diff = " ".join(diff_tokens)
            
            # Cleanup
            diff = re.sub(r'^\W+|\W+$', '', diff) # trim non-alphanumeric
            
            # Remove weights from variant text if they are redundant (optional)
            
            if diff:
                variants.append(diff.title())
            else:
                # If exact match, look for weight difference
                w_text = item.get('weight_text', '')
                if w_text: variants.append(w_text)

        # Unique & Limit
        unique = sorted(list(set(variants)))
        # Filter out empty or pure punctuation
        unique = [u for u in unique if re.search(r'[a-zA-Z0-9]', u)]
        
        if not unique: return ""
        
        return ", ".join(unique[:3]) + (", ..." if len(unique) > 3 else "")

    def group_items(self, items):
        """
        Greedy Clustering Strategy.
        Sorts items, then for each ungrouped item (leader),
        finds ALL other compatible items in the remaining list.
        """
        if not items: return []
        
        # 1. SORTING
        # Sort by Head Word -> Price -> Name
        def sort_key(x):
            name_clean = self.clean_name(x['name'])
            tokens = name_clean.split()
            head = tokens[0] if tokens else ""
            return (head, x.get('price', 0), x['name'])
            
        sorted_items = sorted(items, key=sort_key)
        
        groups = []
        processed_indices = set()
        
        for i in range(len(sorted_items)):
            if i in processed_indices:
                continue
                
            leader = sorted_items[i]
            current_group = [leader]
            processed_indices.add(i)
            
            # Greedy Search: Scan all subsequent items
            for j in range(i + 1, len(sorted_items)):
                if j in processed_indices:
                    continue
                    
                candidate = sorted_items[j]
                
                # --- MATCH LOGIC ---
                is_match = False
                
                # Price Check
                p1 = leader.get('price', 0.0)
                p2 = candidate.get('price', 0.0)
                price_ok = True
                if p1 > 0 and p2 > 0:
                    price_ok = self.check_value_similarity(p1, p2, threshold_ratio=1.6)
                
                # Similarity Check
                score = self.calculate_similarity_score(leader, candidate)
                
                # Decision Matrix
                if price_ok:
                    if score > 0.60: # Threshold for similar price
                        is_match = True
                else:
                    # Price differs significantly -> Require very high similarity (Size variants)
                    if score > 0.85:
                        is_match = True
                        
                        # Extra Safety: Check units match if extracting weights
                        w1, u1 = self.extract_weight_data(leader.get('weight_text') or leader['name'])
                        w2, u2 = self.extract_weight_data(candidate.get('weight_text') or candidate['name'])
                        if w1 and w2 and u1 != u2:
                            is_match = False # Different units (kg vs l) -> unlikely match
                            
                if is_match:
                    current_group.append(candidate)
                    processed_indices.add(j)
            
            groups.append(current_group)
            
        return groups