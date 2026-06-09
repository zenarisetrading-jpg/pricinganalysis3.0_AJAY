import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.price_benchmarking.discovery_service import trigger_background_discovery

def main():
    for client in ["oneshot_uae", "s2c_test"]:
        print("\n" + "="*60)
        print(f"Running production background discovery and analysis for: {client}")
        print("="*60)
        res = trigger_background_discovery(client, force=True)
        print("Result:", res)
        print("="*60)

if __name__ == "__main__":
    main()
