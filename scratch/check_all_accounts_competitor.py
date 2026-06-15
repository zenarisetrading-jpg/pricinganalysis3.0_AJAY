import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
from features.price_benchmarking.saddl_db import execute_saddl_query, fetch_saddl_accounts

# Step 1: Get all active accounts
accounts = fetch_saddl_accounts()
print("=== ALL ACTIVE ACCOUNTS ===")
for a in accounts:
    print(f"  {a['client_id']} | {a['client_name']}")
print()

# Step 2: For each account, run the coverage check
for account in accounts:
    account_id = account['client_id']
    acct_name = account['client_name']
    print(f"\n{'='*60}")
    print(f"ACCOUNT: {acct_name} ({account_id})")
    print(f"{'='*60}")

    # Get BSR categories for this account (last 90 days)
    q_bsr = """
        SELECT DISTINCT b.category_id, b.category_name, COUNT(*) as bsr_rows
        FROM sc_raw.bsr_history b
        WHERE b.account_id = %s
          AND b.report_date >= (CURRENT_DATE - INTERVAL '90 days')
          AND b.category_id IS NOT NULL
        GROUP BY b.category_id, b.category_name
        ORDER BY b.category_name
    """
    bsr_cats = execute_saddl_query(q_bsr, (account_id,))
    if not bsr_cats:
        print("  [NO BSR DATA] - skipping")
        continue

    bsr_cat_ids = [str(r[0]) for r in bsr_cats]
    print(f"  BSR categories (last 90 days): {len(bsr_cats)}")

    # Check what's in competitor_pricing for these categories
    # WITHOUT marketplace filter (correct approach)
    have_data = []
    missing = []
    has_wrong_mp = []  # categories where data is under unexpected marketplace_id

    for r in bsr_cats:
        cat_id = str(r[0])
        cat_name = r[1]

        # Check by category_id only (no marketplace filter)
        rows_any = execute_saddl_query(
            "SELECT marketplace_id, COUNT(*) FROM sc_raw.competitor_pricing WHERE category_id = %s GROUP BY marketplace_id",
            (r[0],)
        )

        if not rows_any:
            missing.append((cat_id, cat_name))
        else:
            total = sum(row[1] for row in rows_any)
            marketplaces = {row[0]: row[1] for row in rows_any}
            has_uae = 'A2VIGQ35RCS4UG' in marketplaces
            has_ksa = 'A17E79C6D8DWNP' in marketplaces
            
            have_data.append((cat_id, cat_name, total, marketplaces))
            
            mp_str = ', '.join(f"{mp}={cnt}" for mp, cnt in marketplaces.items())
            if not has_uae and has_ksa:
                marker = "[KSA only - OLD BUG would miss this]"
            elif has_uae:
                marker = "[UAE - correct]"
            else:
                marker = "[other marketplace]"
            print(f"    [HAS DATA] {cat_name} (id={cat_id}) -> {total} rows | {mp_str} {marker}")

    for cat_id, cat_name in missing:
        print(f"    [MISSING]  {cat_name} (id={cat_id}) -> NO DATA in sc_raw.competitor_pricing")

    print(f"\n  Summary: {len(have_data)}/{len(bsr_cats)} categories have competitor data, {len(missing)}/{len(bsr_cats)} missing")
    
    # Count how many would have been missed by old UAE filter
    missed_by_old_filter = sum(
        1 for _, _, _, mps in have_data
        if 'A2VIGQ35RCS4UG' not in mps  # not UAE
    )
    if missed_by_old_filter:
        print(f"  ** {missed_by_old_filter} categories were SILENTLY MISSED by old marketplace_id='UAE' filter **")
    else:
        print(f"  All data is under UAE marketplace_id - old filter would have worked fine.")
