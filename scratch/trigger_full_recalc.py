import sys
sys.path.insert(0, '.')
from features.price_benchmarking.discovery_service import trigger_background_discovery

print("RUNNING FULL RECALCULATION WORKFLOW FOR oneshot_uae:")
res = trigger_background_discovery('oneshot_uae')
print(f"Workflow completed: {res}")
