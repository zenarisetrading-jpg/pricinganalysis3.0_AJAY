from db import get_supabase_client
from datetime import date, timedelta

def seed_audit_data():
    supabase = get_supabase_client()
    client_id = "s2c-uae"
    
    print("Seeding Audit performance data...")
    
    # 7 days of data for ASIN B001
    for i in range(7):
        target_date = date.today() - timedelta(days=i)
        supabase.table("pb_client_performance_daily").upsert({
            "client_id": client_id,
            "marketplace": "UAE",
            "asin": "B001",
            "performance_date": str(target_date),
            "units_ordered": 10 + i,
            "sessions": 100 + (i * 5),
            "acos": 25.0 + (i * 2),
        }, on_conflict="client_id,asin,marketplace,performance_date").execute()

    print("Audit data seeded successfully!")

if __name__ == "__main__":
    seed_audit_data()
