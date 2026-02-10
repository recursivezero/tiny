# Tiny URL Generator

> A modern, Bitly-style tiny URL web application built with FastAPI & MongoDB

![Python](https://img.shields.io/badge/Python-3.10-blue.svg)
![MongoDB](https://img.shields.io/badge/Database-MongoDB-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

---

## Overview

**tiny URL** is a sleek, fast, and modern URL shortening platform built using **FastAPI**, and **MongoDB**.  
It converts long URLs into short, shareable links — just like Bitly.

The project supports:

- 🚀 **FastAPI REST API** (developers / integrations)

---

## Features

### User Features

- Convert long URLs into short, unique codes
- Default checkbox QR code generation
- Clean Bitly-style result card
- Copy & share buttons
- Download URL button
- Share URL
- Copy button with animation
- Smooth URL validation and sanitization
- Auto Dark/Light Mode (saves preference)
- Mobile-friendly QR Codes
- Fully responsive design
- Recent URLs page

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

| Layer       | Technology            |
| ----------- | --------------------- |
| API Backend | FastAPI               |
| Database    | MongoDB               |
| Frontend    | HTML, CSS, Vanilla JS |
| API Server  | Uvicorn               |
| Validation  | Pydantic v2           |
| CLI         | Click                 |
| Data        | JSON                  |

| Layer       | Technology            |
| ----------- | --------------------- |
| UI Backend  | FastAPI               |
| API Backend | FastAPI               |
| Database    | MongoDB (Optional)    |
| Frontend    | HTML, CSS, Vanilla JS |
| QR Code     | qrcode + Pillow       |
| API Server  | Uvicorn               |
| Validation  | Pydantic v2           |
| Env Mgmt    | python-dotenv         |
| Tooling     | Poetry                |

---

## Project Folder Structure

```text
Directory structure:
tiny/
├── CHANGELOG.md
├── LICENSE
├── app/
│   ├──__init__.py
│   ├── main.py
│   ├── cli.py
│   ├── api/
|   |   └──__init__.py
│   │   └── fast_api.py
|   ├──assets/images
│   ├── db/
|   |    └──__init__.py
|   |     └──data.py
|   ├── static/
|   |     └── images
|   |      └── qr
|   |      └── style.css
|   ├── templates/
|   |        └── index.html
|   |        └── recent.html
│   ├── utils/
|   |     └── __init__.py
|   |     └── _version.py
|   |     └── config.py
|   |     └── helper.py
|   |     └── lint.py
|   |     └── qr.py
|
├── docs/
|    └── build-test.md
|    └─ run_with_curl.md
|
├── request/
|    └── mixed.json
|    └── single.json
|    └── urls.json
├── pyproject.toml
|    └── poetry.lock
├──README.md
|    └── CHANGELOG.md
|    └── requirements.txt
├── tiny.code-workspace
└── .gitignore

```

⚙️ How to Run the Project Locally

## How to start

```sh
poetry install
```

### 3. Install with MongoDB Support (Optional)

```sh
poetry install --with mongodb
```

---

## Running the App

```sh
poetry run uvicorn app.main:app --reload
```

or

```sh
poetry run tiny dev
```

Open:
http://127.0.0.1:8000

---

## Environment Configuration

```
ENV=development
DOMAIN=http://127.0.0.1:8000
MONGO_URI=mongodb://<user>:<password>@localhost:27017/tiny_url?authSource=tiny_url
DATABASE_NAME=tiny_url
```

Supported env files:

- .env.development
- .env.local
- .env (production)

---

## Offline Mode (No Database)

TinyURL supports graceful offline mode.

### What works

- App starts normally
- UI loads
- Short URLs are generated
- QR codes are generated

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

### With MongoDB

```sh
poetry install --with mongodb
sudo systemctl start mongod
poetry run tiny dev
```

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

## REST API (FastAPI)

### API Base URL

http://127.0.0.1:8000/api

### Swagger Docs

http://127.0.0.1:8000/api/docs

### Shorten URL

POST /api/shorten

Request:

```json
{
  "url": "https://example.com"
}
```

Response:

```json
{
  "input_url": "https://example.com",
  "output_url": "http://127.0.0.1:8000/AbX92p",
  "created_on": "2026-01-03T13:25:10+00:00"
}
```

### API Version

GET /api/version

Response:

```json
{
  "version": "0.1.0"
}
```

---

## Troubleshooting

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
poetry run uvicorn app.main:app --reload
```

---

## License

📜Docs
[run_with_curl](run_with_curl)

Screenshots:
Home Page:
![home page](./assets/images/home.png)
![home dark mode](./assets/images/home_dark.png)
![home page](./assets/images/valid.png)
![home layout](./assets/images/short_url.png)
![recent](./assets/images/recent.png)
tiny API Page:
![API](./assets/images/API_page.png)
![API1](./assets/images/api_page2.png)

📜License

[MIT](LICENSE)
