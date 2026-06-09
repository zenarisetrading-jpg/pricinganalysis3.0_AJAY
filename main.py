from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from features.price_benchmarking import routes as pb_routes


app = FastAPI(title="Price Benchmarking")

app.include_router(pb_routes.router, prefix="/api/v1/benchmarking", tags=["benchmarking"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def price_benchmarking_dashboard() -> str:
    dashboard_path = Path(__file__).resolve().parent / "dashboard" / "price_benchmarking.html"
    return dashboard_path.read_text(encoding="utf-8")
