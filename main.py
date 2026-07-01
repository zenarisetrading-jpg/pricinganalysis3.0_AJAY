from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Cookie, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

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


from fastapi import Request
from features.auth import routes as auth_routes

app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["auth"])

@app.get("/", response_class=HTMLResponse)
async def price_benchmarking_dashboard(request: Request) -> Response:
    # Check for access token cookie, redirect to login if missing
    token = request.cookies.get("access_token")
    if not token:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/login")

    dashboard_path = Path(__file__).resolve().parent / "dashboard" / "price_benchmarking.html"
    content = dashboard_path.read_text(encoding="utf-8")
    return Response(
        content=content,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page() -> Response:
    login_path = Path(__file__).resolve().parent / "dashboard" / "login.html"
    content = login_path.read_text(encoding="utf-8")
    return Response(
        content=content,
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
