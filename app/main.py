# app/main.py
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.templating import Jinja2Templates
from app.routes import ui_router
from app.utils import db
from app.utils.cache import cleanup_expired

# -----------------------------
# Background cache cleanup task
# -----------------------------
from app.utils.config import (
    CACHE_TTL,
    SESSION_SECRET,
    QR_DIR,
)


async def cache_health_check():
    logger = logging.getLogger(__name__)
    logger.info("🧹 Cache cleanup task started")

    interval = max(1, CACHE_TTL // 3)  # pure TTL-based

    logger.info(f"🕒 Cache cleanup interval set to {interval}s")

    while True:
        try:
            cleanup_expired()
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
        await asyncio.sleep(interval)


# -----------------------------
# Lifespan: env + DB connect ONCE (DB-optional)
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger(__name__)
    logger.info("Application startup: Initializing services...")

    # DB init (optional)
    db_ok = db.connect_db()
    if db_ok:
        db.start_health_check()
        logger.info("🟢 MongoDB enabled")
    else:
        logger.warning("🟡 MongoDB disabled (cache-only mode)")

    # Cache TTL cleanup
    cache_task = asyncio.create_task(cache_health_check())
    logger.info("🧹 Cache TTL cleanup enabled")

    logger.info("Application startup complete")
    yield

    logger.info("Application shutdown: Cleaning up...")

    # Stop cache task
    cache_task.cancel()
    try:
        await cache_task
    except asyncio.CancelledError:
        logger.info("🧹 Cache cleanup task stopped")

    # Stop DB health check
    try:
        await db.stop_health_check()
    except Exception as e:
        logger.error(f"Error stopping health check: {str(e)}")

    # Close Mongo client if exists
    try:
        if db.client is not None:
            db.client.close()
            logger.info("MongoDB client closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB client: {str(e)}")

    logger.info("Application shutdown complete")


app = FastAPI(title="TinyURL", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
templates = Jinja2Templates(directory="app/templates")

# Mount QR static files
BASE_DIR = Path(__file__).resolve().parent

# Mount QR static files
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)
# Ensure QR directory exists at startup
QR_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/qr",
    StaticFiles(directory=str(QR_DIR)),
    name="qr",
)


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):

    # If it's API/UI route → return JSON
    if request.url.path.startswith("/cache") or request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail},
        )

    # If it's browser route → return HTML page
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "404.html",
            {"request": request},
            status_code=404,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )


# -----------------------------
# Routers (UI + API)
# -----------------------------
app.include_router(ui_router)  # UI routes at "/"
