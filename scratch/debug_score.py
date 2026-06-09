import sys
sys.path.insert(0, '.')
from features.price_benchmarking.relevance_filter import calculate_relevance_score, get_tokens, difflib

ref = 'Electrolyte '
title = 'LMNT Zero Sugar Electrolytes - Lemonade | Drink Mix | 18-Count'

ref_tokens = get_tokens(ref)
cand_tokens = get_tokens(title)
print(f"ref_tokens: {ref_tokens}")
print(f"cand_tokens: {cand_tokens}")

fuzzy_ratio = difflib.SequenceMatcher(None, ref.lower(), title.lower()).ratio()
print(f"fuzzy_ratio: {fuzzy_ratio:.4f}")

match_count = 0
total_weight = 0
for i, token in enumerate(ref_tokens):
    weight = 2.0 if i < 3 else 1.0
    total_weight += weight
    if token in cand_tokens:
        match_count += weight
        print(f"  Matched: '{token}' (weight {weight})")

keyword_score = match_count / total_weight if total_weight > 0 else 0
print(f"keyword_score: {keyword_score:.4f}")

# Product Type Heuristic
form_factors = {"powder", "tablet", "liquid", "capsule", "gummi", "softgel", "drink"}
ref_forms = set(ref_tokens).intersection(form_factors)
cand_forms = set(cand_tokens).intersection(form_factors)
print(f"ref_forms: {ref_forms} | cand_forms: {cand_forms}")

form_penalty = 0.0
if ref_forms and cand_forms and ref_forms.isdisjoint(cand_forms):
    form_penalty = 0.3
print(f"form_penalty: {form_penalty:.4f}")

final_score = (fuzzy_ratio * 0.4) + (keyword_score * 0.6) - form_penalty
print(f"final_score: {final_score:.4f}")
