from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.db.data import urls as urls_collection
from app.utils.helper import generate_code, is_valid_url, sanitize_url
from app import __version__


app = FastAPI(
    title="Tiny API",
    version=__version__,
    description="Tiny URL Shortener API built with FastAPI",
)




class ShortenRequest(BaseModel):
    url: str = Field(..., example="https://example.com")


class ShortenResponse(BaseModel):
    input_url: str
    output_url: str
    created_on: datetime


class VersionResponse(BaseModel):
    version: str
@app.get("/", response_class=HTMLResponse, tags=["Home"])
async def read_root(request: Request):
    return """
    <html>
        <head>
            <title>🌙 tiny API 🌙</title>
            <style>
                body {
                    margin: 0;
                    height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(180deg, #0b1220, #050b14);
                    font-family: "Poppins", system-ui, Arial, sans-serif;
                    color: #f8fafc;
                }

                .card {
                    background: rgba(255, 255, 255, 0.06);
                    backdrop-filter: blur(12px);
                    border-radius: 16px;
                    padding: 50px 40px;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
                    max-width: 520px;
                    width: 90%;
                }

                h1 {
                    font-size: 2.8em;
                    margin-bottom: 12px;
                    background: linear-gradient(90deg, #5ab9ff, #4cb39f);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }

                p {
                    font-size: 1.1em;
                    color: #cbd5e1;
                    margin-bottom: 30px;
                }

                a {
                    display: inline-block;
                    padding: 14px 26px;
                    border-radius: 12px;
                    background: linear-gradient(90deg, #4cb39f, #5ab9ff);
                    color: #fff;
                    text-decoration: none;
                    font-weight: 700;
                    transition: transform 0.2s ease, box-shadow 0.2s ease;
                }

            </style>
        </head>
        <body>
            <div class="card">
                <h1>🚀 tiny API</h1>
                <p>FastAPI backend for the Tiny URL shortener</p>
                <a href="/docs">View API Documentation</a>
            </div>
        </body>
    </html>
    """

@app.post(
    "/api/shorten",
    response_model=ShortenResponse,
    status_code=201,
    summary="Shorten a URL",
    description="Generate a short URL for a given long URL",
    tags=["URL"],
)
def shorten_url(payload: ShortenRequest):
    original_url = sanitize_url(payload.url)

    if not is_valid_url(original_url):
        raise HTTPException(status_code=400, detail="Invalid URL")

    short_code = generate_code()
    while urls_collection.find_one({"short_code": short_code}):
        short_code = generate_code()

    created_at = datetime.now(timezone.utc)

    urls_collection.insert_one(
        {
            "short_code": short_code,
            "original_url": original_url,
            "created_at": created_at,
            "visit_count": 0,
        }
    )

    return ShortenResponse(
        input_url=original_url,
        output_url=f"http://127.0.0.1:8001/{short_code}",
        created_on=created_at,
    )


@app.get(
    "/api/version",
    response_model=VersionResponse,
    summary="API version",
    tags=["Meta"],
)
def version():
    return VersionResponse(version=__version__)
