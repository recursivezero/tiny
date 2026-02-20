# app/main.py
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.routes import ui_router, api_router
from app.utils import db
from app.utils.config import SESSION_SECRET


# -----------------------------
# Lifespan: env + DB connect ONCE (DB-optional)
# -----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger(__name__)
    logger.info("Application startup: Initializing services...")

    db_ok = db.connect_db()
    if db_ok:
        db.start_health_check()
        logger.info("🟢 MongoDB enabled")
    else:
        logger.warning("🟡 MongoDB disabled (cache-only mode)")

    logger.info("Application startup complete")
    yield

    logger.info("Application shutdown: Cleaning up...")

    try:
        await db.stop_health_check()
    except Exception as e:
        logger.error(f"Error stopping health check: {str(e)}")

    try:
        if db.client is not None:
            db.client.close()
            logger.info("MongoDB client closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB client: {str(e)}")

    logger.info("Application shutdown complete")


app = FastAPI(title="TinyURL", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# -----------------------------
# Global error handler
# -----------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "INTERNAL_SERVER_ERROR"},
    )


# -----------------------------
# Routers (UI + API)
# -----------------------------
app.include_router(ui_router)  # UI routes at "/"
app.include_router(api_router)  # API routes at "/api"
