import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import recalculate_parent_from_categories

print("RECALCULATING FOR B0DLX3GJNJ:")
res1 = recalculate_parent_from_categories('oneshot_uae', 'B0DLX3GJNJ')
print(f"Status: {res1.get('status')} | Recs: {len(res1.get('recommendations', []))}")
if 'recommendations' in res1 and res1['recommendations']:
    rec = res1['recommendations'][0]
    print(f"  Reasoning: {rec.get('reasoning')}")

print("\nRECALCULATING FOR B0FNN5WKDG:")
res2 = recalculate_parent_from_categories('oneshot_uae', 'B0FNN5WKDG')
print(f"Status: {res2.get('status')} | Recs: {len(res2.get('recommendations', []))}")
if 'recommendations' in res2 and res2['recommendations']:
    rec = res2['recommendations'][0]
    print(f"  Reasoning: {rec.get('reasoning')}")
