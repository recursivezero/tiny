# Build & Test Guide (Tiny URL Project)

This document explains how to **build**, **install**, and **run tests locally** for the Tiny URL project using Poetry, FastAPI (API), and Fast(UI).

---

## ✅ Prerequisites

- Python 3.10+
- Poetry installed
- MongoDB running locally
- `.env.local` file created (not committed to Git)

Example `.env.local`:

📦 1. Install Dependencies

```
poetry install
```

🏗️ 2. Build the Project

This creates a source distribution and wheel package:

```
poetry build
```

Expected output:

```
Built tiny-0.0.1.tar.gz
Built tiny-0.0.1-py3-none-any.whl
```

🧪 3. Test the Built Wheel

Create a clean virtual environment and install the wheel:

```
python3 -m venv /tmp/tiny-test
source /tmp/tiny-test/bin/activate

pip install dist/tiny-0.0.1-py3-none-any.whl
```

Verify imports:

```
python -c "import app; print('app import OK')"
```

🚀 4. Run API & UI Together (Two Terminals)

Run both services in separate terminals.

Terminal 1 – FastAPI (API)

```
poetry run uvicorn app.api.fast_api:app --reload --port 8001
```

API will run at:

```json
http://127.0.0.1:8000
```

Docs:

```json
http://127.0.0.1:8000/docs
```

Terminal 2 – Fast (UI)

```
poetry run uvicorn app.main:app --reload

```

UI will run at:

```json
http://127.0.0.1:5000
```
