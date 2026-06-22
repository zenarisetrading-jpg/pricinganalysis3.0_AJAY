from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from features.price_benchmarking import routes as pb_routes
from features.price_benchmarking.saddl_db import get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_pool()  # warm SADDL connection pool before first request
    yield


app = FastAPI(title="Price Benchmarking", lifespan=lifespan)

app.include_router(pb_routes.router, prefix="/api/v1/benchmarking", tags=["benchmarking"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def price_benchmarking_dashboard() -> str:
    dashboard_path = Path(__file__).resolve().parent / "dashboard" / "price_benchmarking.html"
    return dashboard_path.read_text(encoding="utf-8")
