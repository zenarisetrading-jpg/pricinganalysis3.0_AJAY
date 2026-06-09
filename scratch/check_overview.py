import sys
sys.path.append('d:/pricing_analysis')
import asyncio
from features.price_benchmarking.routes import get_overview

async def test():
    res = await get_overview(client_id="s2c_test")
    print(f"parent_asin_count: {res.get('parent_asin_count')}")
    print(f"rows length: {len(res.get('rows', []))}")

asyncio.run(test())
