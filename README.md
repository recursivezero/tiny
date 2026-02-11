# Tiny URL Generator

> A modern, Bitly-style tiny URL web application built with FastAPI, optional MongoDB, and a sleek web UI.

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-teal.svg)
![MongoDB](<https://img.shields.io/badge/Database-MongoDB%20(Optional)-green.svg>)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

---

## Overview

Tiny URL is a sleek, fast, and modern URL shortening platform built using FastAPI with optional MongoDB persistence.
It converts long URLs into short, shareable links — just like Bitly.

The project supports:

- Web UI (FastAPI + Jinja templates)
- REST API (FastAPI)
- Offline Mode (No MongoDB required)

This project is designed with:

- Clean startup lifecycle (no racing configs)
- Optional database dependency
- Graceful degradation when MongoDB is unavailable
- In-memory cache fallback
- QR code generation with auto folder creation

---

## Features

### User Features

- Convert long URLs into short, unique codes
- Default checkbox QR code generation
- Clean Bitly-style result card
- Copy & share buttons
- Download URL button
- URL validation and sanitization
- Fully responsive UI
- Recent URLs page (when DB is available)
- Visit count tracking (when DB is available)
- QR image auto-generation with logo
- Cache-accelerated redirects

### API & Developer Features

- REST API for URL shortening
- API version endpoint
- Swagger / OpenAPI documentation
- API landing page
- Cache layer for fast redirects
- Graceful offline mode (no DB required)
- Clean startup lifecycle using FastAPI lifespan
- Optional MongoDB dependency

---

## Short Code Generation Algorithm

The app uses a Random Alphanumeric Short Code Generator.

### Algorithm Details

- Uses `string.ascii_letters + string.digits`
- Randomly picks characters
- Generates a 6-character short ID
- Checks MongoDB for collisions (if DB is enabled)
- Automatically regenerates on collision

### Example

```python
import random, string

def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))
```

---

## Tech Stack

| Layer       | Technology              |
| ----------- | ----------------------- |
| UI Backend  | FastAPI                 |
| API Backend | FastAPI                 |
| Database    | MongoDB (Optional)      |
| Cache       | In-Memory (Python dict) |
| Frontend    | HTML, CSS, Vanilla JS   |
| QR Code     | qrcode + Pillow         |
| API Server  | Uvicorn                 |
| Validation  | Pydantic v2             |
| Env Mgmt    | python-dotenv           |
| Tooling     | Poetry                  |

---

[Project Tree](./docs/tree.md)

## ⚙️ How to Run the Project Locally

`Virtual Environment Configuration`

```bash
poetry config virtualenvs.path /your/desired/path
```

## Environment Configuration

Ensure below files are configured (create if not exist) properly to run the project;

Supported env files:

- .env.development
- .env.local
- .env (production)

```text
ENV=development
DOMAIN=http://127.0.0.1:8000
MONGO_URI=mongodb://<user>:<password>@localhost:27017/tiny_url?authSource=tiny_url
DATABASE_NAME=tiny_url
```

## Install Dependencies

```bash
poetry lock --no-cache --regenerate
poetry install  --all-extras --with dev
```

Or manually

```bash
poetry install
```

## How to Run

```bash
poetry run tiny dev
```

Access: <http://127.0.0.1:8000>

## Run FastAPI Server

```bash
poetry run tiny api
```

Access: <http://127.0.0.1:8001>

## Offline Mode (No Database)

TinyURL supports graceful offline mode.

### What works

- App starts normally
- UI loads
- Short URLs are generated
- QR codes are generated
- Redirects work from in-memory cache

### What is disabled

- Recent URLs page
- Persistent redirects after restart
- Visit count tracking

Offline Mode activates automatically when:

- MongoDB is down
- OR pymongo is not installed
- OR MONGO_URI is missing/invalid

Log message:

```
⚠️ MongoDB connection failed. Running in NO-DB mode.
```

---

## Switching Modes

### Without MongoDB

```sh
sudo systemctl stop mongod
poetry run tiny dev
```

or

```sh
poetry run pip uninstall pymongo
poetry run tiny dev
```

---

## Troubleshooting

sometimes there might be chances that virtual environment get corrupted then delete the old virtual environment and start afresh.

```sh
poetry env info
# this will provide virtual environment name
poetry env remove <environment-full-name>
```

### Mongo auth error

Encode special chars:

@ ? %40

Example:

```
MONGO_URI=mongodb://user%40gmail.com:Pass%40123@localhost:27017/tiny_url?authSource=tiny_url
```

---

## WSL Notes

```sh
sudo systemctl start mongod
poetry run tiny dev
```

## Build & Packaging

## Build Package

```bash
poetry clean
poetry build
```

Artifacts in `dist/`

- tiny-x.y.0-py3-none-any.whl
- tiny-x.y.0.tar.gz

## Test Locally

```bash
python -m venv .venv-dist
source .venv-dist/bin/activate
# Windows
.venv-dist\Scripts\activate
```

### Install package

```bash
pip install dist/*.whl
pip install --upgrade dist/*.whl
```

## License

📜Docs
[run_with_curl](docs/run_with_curl)

Screenshots:
Home Page:
![home page](assets/images/home.png)
![home dark mode](assets/images/home_dark.png)
![home page](assets/images/valid.png)
![home layout](assets/images/short_url.png)
![recent](assets/images/recent.png)
tiny API Page:
![API](assets/images/API_page.png)
![API1](assets/images/api_page2.png)
No DB Mode:
![NO DB](assets/images/no-db.png)
📜License

[MIT](LICENSE)
