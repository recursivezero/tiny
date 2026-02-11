## Project Folder Structure

```text
Directory structure:
tiny/
├── CHANGELOG.md
├── LICENSE
├── README.md
├── app/
│   ├──__init__.py
│   ├── main.py
│   ├── cli.py
│   ├── api/
│   │   └── fast_api.py
|   ├──assets/images
│   ├── db/
|   |    └──__init__.py
|   |     └──data.py
│   ├── static/
|   |     └── images
|   |     └── qr
|   |     └──style.css
|   └── templates/
|   |        └── index.html
|   |        └── recent.html
|   |        └── coming-soon.html
│   ├── utils/
|   |     └──__init__.py
|   |     └──_version.py
|   |     └── cache.py
|   |     └── config.py
|   |     └── helper.py
|   |     └── lint.py
|   |     └── qr.py
├── docs/
|    └── build-test.md
|    └── cache.md
|    └── run_with_curl.md
├── pyproject.toml
|    └── poetry.lock
├──README.md
|    └── CHANGELOG.md
|    └── requirements.txt
├── tiny.code-workspace
└── .gitignore

```
