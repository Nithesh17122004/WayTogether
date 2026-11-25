# WayTogether API

## Requirements
- Python 3.11 or newer
- PostgreSQL for shared development/production; SQLite is used by default locally.

## Setup
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Health check: http://127.0.0.1:8000/api/v1/health/

Do not use the development SECRET_KEY in production. Configure DATABASE_URL, allowed hosts, HTTPS and CORS through the deployment environment.
