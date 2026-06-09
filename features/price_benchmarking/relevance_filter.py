import re
from typing import List, Dict, Any, Set

def get_tokens(text: str) -> List[str]:
    """Normalize and tokenize text, preserving all words (even short ones)."""
    if not text:
        return []
    # Split by spaces and commas, lowercased
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    return [t.strip() for t in text.split() if t.strip()]

def parse_exclusions(exclude_keywords_str: str | None) -> tuple[List[str], List[str]]:
    """Parse the exclude_keywords string into (keywords, brands)."""
    if not exclude_keywords_str or not str(exclude_keywords_str).strip():
        return [], []
    
    parts = str(exclude_keywords_str).split("|brand_exclude:")
    kws_part = parts[0]
    brands_part = parts[1] if len(parts) > 1 else ""
    
    kws = [kw.strip().lower() for kw in kws_part.split(",") if kw.strip()]
    brands = [b.strip().lower() for b in brands_part.split(",") if b.strip()]
    return kws, brands

def match_brand(competitor_brand: str | None, excluded_brands: List[str]) -> bool:
    """
    Check if the competitor's brand matches any of the excluded brands.
    Uses space normalization, case-insensitive, and regex word-boundary matching.
    """
    if not competitor_brand or not excluded_brands:
        return False
        
    # Normalize competitor brand: lowercase, remove extra spaces
    comp_brand_clean = " ".join(str(competitor_brand).lower().split())
    if not comp_brand_clean:
        return False
        
    for brand in excluded_brands:
        brand_clean = " ".join(brand.lower().split())
        if not brand_clean:
            continue
            
        # Exact match
        if comp_brand_clean == brand_clean:
            return True
            
        # Regex word-boundary match (e.g., "stanley" matches "stanley pmi" or "stanley cups")
        pattern = r"\b" + re.escape(brand_clean) + r"\b"
        if re.search(pattern, comp_brand_clean):
            return True
            
    return False

def calculate_relevance_score(reference_name: str, candidate_title: str) -> float:
    """
    Calculate a relevance score between 0.0 and 1.0.
    Under multiple keyword search:
    - Comma ',' splits alternative queries (OR condition).
    - Within each comma-separated phrase, spaces split mandatory terms (AND condition).
    If candidate_title matches any of the comma-separated phrases, return 1.0. Otherwise 0.0.
    """
    if not reference_name or not reference_name.strip():
        return 1.0

    if not candidate_title:
        return 0.0

    ref_query = reference_name.lower()
    # Split by comma (OR)
    phrases = [p.strip() for p in ref_query.split(",") if p.strip()]
    if not phrases:
        return 1.0

    title_lower = candidate_title.lower()

    # Check if ANY of the comma-separated phrases match (OR)
    for phrase in phrases:
        # Split the phrase by spaces (AND)
        keywords = [kw.strip() for kw in phrase.split() if kw.strip()]
        if not keywords:
            continue
        
        # A phrase matches only if ALL of its space-separated keywords are in the title (AND)
        phrase_matches = True
        for kw in keywords:
            if kw not in title_lower:
                phrase_matches = False
                break
        
        if phrase_matches:
            return 1.0

    return 0.0

def is_related(
    target_product: Dict[str, Any],
    candidate_product: Dict[str, Any],
    threshold: float = 0.4
) -> bool:
    """
    Check if a candidate product is related to the target product.
    Always returns True for variations of the same parent group.
    """
    # 1. Variations / Parent Group (Always Keep)
    target_parent = target_product.get("parent_asin")
    candidate_parent = candidate_product.get("parent_asin")
    if target_parent and candidate_parent and target_parent == candidate_parent:
        return True
        
    candidate_title = candidate_product.get("title", "")
    candidate_brand = candidate_product.get("brand", "")
    
    exclude_keywords_str = target_product.get("exclude_keywords")
    if exclude_keywords_str and str(exclude_keywords_str).strip():
        exclude_keywords, exclude_brands = parse_exclusions(exclude_keywords_str)
        if any(kw in candidate_title.lower() for kw in exclude_keywords):
            return False
        if match_brand(candidate_brand, exclude_brands):
            return False
    
    # 2. Use Reference Name
    reference = target_product.get("reference_name")
    if not reference or str(reference).strip() == "":
        return True
    
    score = calculate_relevance_score(reference, candidate_title)
    return score >= threshold

def filter_related_products(
    target_product: Dict[str, Any],
    candidate_products: List[Dict[str, Any]],
    exclude_asins: List[str] | Set[str] | None = None
) -> List[Dict[str, Any]]:
    """Filter the candidate competitor pool based on reference name keyword matching and exclude keywords."""
    reference = target_product.get("reference_name")
    exclude_keywords_str = target_product.get("exclude_keywords")
    exclude_set = set(exclude_asins or [])
    if target_product.get("asin"):
        exclude_set.add(target_product["asin"])
    
    # Parse exclude keywords and brands
    exclude_keywords, exclude_brands = parse_exclusions(exclude_keywords_str)
    
    # If no keyword is provided, do not filter by keyword. But we STILL filter by exclude keywords & brands.
    if not reference or str(reference).strip() == "":
        results = []
        for p in candidate_products:
            if p.get("asin") in exclude_set:
                continue
                
            title_lower = p.get("title", "").lower()
            if any(kw in title_lower for kw in exclude_keywords):
                continue
                
            brand_val = p.get("brand")
            if match_brand(brand_val, exclude_brands):
                continue
                
            p_copy = p.copy()
            p_copy["relevance_score"] = 1.0
            results.append(p_copy)
        return results

    results = []
    target_parent = target_product.get("parent_asin")
    
    for p in candidate_products:
        if p.get("asin") in exclude_set:
            continue
            
        title_lower = p.get("title", "").lower()
        if any(kw in title_lower for kw in exclude_keywords):
            continue
            
        brand_val = p.get("brand")
        if match_brand(brand_val, exclude_brands):
            continue
            
        score = calculate_relevance_score(reference, p.get("title", ""))
        
        # Variations/Parent match always get 1.0 relevance
        candidate_parent = p.get("parent_asin")
        is_variation = target_parent and candidate_parent and target_parent == candidate_parent
        
        if is_variation:
            score = 1.0
            
        if score >= 0.4 or is_variation:
            p_copy = p.copy()
            p_copy["relevance_score"] = score
            results.append(p_copy)
            
    return results
