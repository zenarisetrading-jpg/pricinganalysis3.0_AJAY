
from db import get_supabase_client
from datetime import datetime, timezone

supabase = get_supabase_client()

def test_save():
    data = {
        "client_id": "oneshot_uae",
        "asin": "B0DGLGPN1N",
        "performance_date": datetime.now(timezone.utc).date().isoformat(),
        "units_ordered": 10,
        "sessions": 100,
        "acos": 0,
        "cvr": 0.1,
        "marketplace": "UAE"
    }
    try:
        # Try simple insert
        res = supabase.table("pb_client_performance_daily").insert(data).execute()
        print(f"Insert Success: {res.data}")
    except Exception as e:
        print(f"Insert Error: {e}")

if __name__ == "__main__":
    test_save()
