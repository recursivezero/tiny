# app/api/fast_api.py
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import __version__
from app.routes import api_router

app = FastAPI(
    title="Tiny API",
    version=__version__,
    description="Tiny URL Shortener API built with FastAPI",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "INTERNAL_SERVER_ERROR"},
    )


# ✅ Single source of truth for API routes only
app.include_router(api_router)
