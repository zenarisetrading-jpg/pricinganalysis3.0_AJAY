import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import fetch_competitors_by_category
from features.price_benchmarking.relevance_filter import calculate_relevance_score, get_tokens, difflib

# Let's override get_tokens with the fixed version in this script
def get_tokens_fixed(text: str) -> list[str]:
    import re
    if not text:
        return []
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    raw_tokens = text.split()
    tokens = []
    for t in raw_tokens:
        if len(t) <= 2:
            continue
        stemmed = t
        if t.endswith('ies'):
            stemmed = t[:-3] + 'y'
        elif t.endswith('s') and not t.endswith('ss'):
            if t.endswith('es') and any(t.endswith(suffix) for suffix in ('shes', 'ches', 'xes', 'zes')):
                stemmed = t[:-2]
            else:
                stemmed = t[:-1]
        tokens.append(stemmed)
    return tokens

def calculate_relevance_score_fixed(reference_name: str, candidate_title: str) -> float:
    if not reference_name or not candidate_title:
        return 0.0

    ref_tokens = get_tokens_fixed(reference_name)
    cand_tokens = get_tokens_fixed(candidate_title)
    
    if not ref_tokens:
        return 0.0

    fuzzy_ratio = difflib.SequenceMatcher(None, reference_name.lower(), candidate_title.lower()).ratio()
    
    match_count = 0
    total_weight = 0
    for i, token in enumerate(ref_tokens):
        weight = 2.0 if i < 3 else 1.0
        total_weight += weight
        if token in cand_tokens:
            match_count += weight
            
    keyword_score = match_count / total_weight if total_weight > 0 else 0
    
    form_factors = {"powder", "tablet", "liquid", "capsule", "gummi", "softgel", "drink"}
    ref_forms = set(ref_tokens).intersection(form_factors)
    cand_forms = set(cand_tokens).intersection(form_factors)
    
    form_penalty = 0.0
    if ref_forms and cand_forms and ref_forms.isdisjoint(cand_forms):
        form_penalty = 0.3

    final_score = (fuzzy_ratio * 0.4) + (keyword_score * 0.6) - form_penalty
    return max(0.0, min(1.0, final_score))

missed_products = [
    ('B0CQPGBBVP', "MuscleTech | Platinum Essential Amino Acids Supplement with Electrolytes | Pre-Workout Powder for Energy, Muscle Growth & Strength Builder for Men & Women | 387 grams | 30 Servings"),
    ('B0CLYGV2J8', "O.R.S Hydration Tablets With Electrolytes, Lemon, Blackcurrant, Strawberry and Orange (Pack Of 4)"),
    ('B0GH25WM4N', "OWNKIND Electrolytes Powder Sachets - Strawberry & Kiwi | Zero Sugar, All 6 Electrolytes, Hydration Multiplier w/Essential Minerals, Vitamins, Immune & Metabolic Functions. Vegan, Sugar & Gluten Free"),
    ('B0F257BKKB', "Optimum Nutrition Creatine Monohydrate Plus Powder, Strawberry Peach Flavored Creatine Performance Blend, with Electrolytes for Hydration, Added Vitamins, 40 Servings, 360 Grams (Packaging May Vary)"),
    ('B0F1BSR4VR', "LMNT Zero Sugar Electrolytes - Lemonade | Drink Mix | 18-Count"),
    ('B0F3D3JW3M', "NBL Natural EAA Hydration | EAAs + BCAA Powder | Muscle Recovery, Strength, Muscle Building, Endurance | 8G Essential Amino Acids + Electrolytes | Strawberry Watermelon 30 Serving"),
    ('B0D1TZBQ23', "Rule1 1 Essential Amino 9 | Blue Razz Lemonade | Supports Muscle Recovery and Electrolytes for Hydration | Dietary Supplement | 30 Servings | 345 grams")
]

print("RELEVANCE SCORES WITH FIXED STEMMING:")
for asin, title in missed_products:
    score_old = calculate_relevance_score('Electrolyte', title)
    score_new = calculate_relevance_score_fixed('Electrolyte', title)
    print(f"  {asin}: old={score_old:.2f}, new={score_new:.2f} | Title: {title[:80]}")
