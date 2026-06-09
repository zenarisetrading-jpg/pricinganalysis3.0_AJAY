
from features.price_benchmarking.relevance_filter import calculate_relevance_score, is_related

def test_relevance():
    # Example from user request: Electrolyte Hydration Powder
    reference = "Electrolyte Hydration Powder"
    
    competitors = [
        {"title": "Liquid I.V. Hydration Multiplier - Electrolyte Powder Packet", "expected": True},
        {"title": "DripDrop Electrolyte Powder Packets - Dehydration Relief", "expected": True},
        {"title": "Optimum Nutrition Gold Standard Whey Protein Powder", "expected": False},
        {"title": "Vitamin C Gummies for Kids and Adults", "expected": False},
        {"title": "Celsius Essential Energy Drink - 12 Fl Oz", "expected": False},
        {"title": "Ultima Replenisher Hydration Electrolyte Powder", "expected": True},
        {"title": "Pure Encapsulations - Magnesium (Glycinate) 120 Capsules", "expected": False}
    ]
    
    print(f"Reference: {reference}\n")
    print(f"{'Relevance':<10} | {'Action':<10} | {'Competitor Title'}")
    print("-" * 80)
    
    for comp in competitors:
        score = calculate_relevance_score(reference, comp["title"])
        related = is_related({"reference_name": reference}, comp)
        action = "KEEP" if related else "EXCLUDE"
        
        print(f"{score*100:>8.1f}% | {action:<10} | {comp['title']}")
        
        if related != comp["expected"]:
            print(f"  --> MISMATCH! Expected {comp['expected']}, got {related}")

if __name__ == "__main__":
    test_relevance()
