import sys
sys.path.insert(0, '.')
import traceback
from features.price_benchmarking.discovery_service import run_competitor_analysis_workflow

try:
    print("Starting competitor analysis workflow for s2c_uae_test...")
    results = run_competitor_analysis_workflow("s2c_uae_test")
    print("Workflow finished successfully!")
    print(f"Workflow status: {results.get('status')}")
    print(f"Workflow message: {results.get('message')}")
    if "results" in results:
        print(f"Results count: {len(results['results'])}")
    else:
        print(f"Details: {results.get('details')}")
except Exception as e:
    print("\n--- ERROR OCCURRED ---")
    traceback.print_exc()
