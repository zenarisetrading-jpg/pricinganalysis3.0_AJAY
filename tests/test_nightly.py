from datetime import date

from features.price_benchmarking.nightly import aggregate_daily


class _Query:
    def __init__(self, payload):
        self.payload = payload

    def select(self, _value):
        return self

    def gte(self, _column, _value):
        return self

    def lt(self, _column, _value):
        return self

    def upsert(self, rows, on_conflict=None):
        self.payload["upsert_rows"] = rows
        self.payload["on_conflict"] = on_conflict
        return self

    def execute(self):
        if self.payload["table"] == "pb_price_events":
            return type("Resp", (), {"data": self.payload["events"]})()
        return type("Resp", (), {"data": self.payload.get("upsert_rows", [])})()


class _SupabaseStub:
    def __init__(self, events):
        self.payload = {"events": events, "upsert_rows": None, "on_conflict": None, "table": None}

    def table(self, name):
        self.payload["table"] = name
        return _Query(self.payload)


def test_aggregate_daily_groups_events_and_upserts_snapshot_rows() -> None:
    supabase = _SupabaseStub(
        events=[
            {
                "asin": "ASIN1",
                "marketplace": "UAE",
                "floor_price": 10.0,
                "ceiling_price": 20.0,
                "median_price": 15.0,
                "buy_box_price": 15.0,
                "foep": 14.0,
            },
            {
                "asin": "ASIN1",
                "marketplace": "UAE",
                "floor_price": 12.0,
                "ceiling_price": 22.0,
                "median_price": 16.0,
                "buy_box_price": 16.0,
                "foep": 15.0,
            },
        ]
    )

    result = aggregate_daily(supabase, target_date=date(2026, 4, 28))

    assert result == {"date": "2026-04-28", "n_asins": 1}
    rows = supabase.payload["upsert_rows"]
    assert rows is not None
    assert len(rows) == 1
    assert rows[0]["asin"] == "ASIN1"
    assert rows[0]["floor_price"] == 10.0
    assert rows[0]["ceiling_price"] == 22.0
    assert supabase.payload["on_conflict"] == "asin,marketplace,snapshot_date"
