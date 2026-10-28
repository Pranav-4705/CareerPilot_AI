# CareerPilot AI - Backend Service

FastAPI-based REST backend for CareerPilot AI.

## Architecture

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── api.py            # API router aggregator
│   │       └── endpoints/
│   │           └── health.py     # Health check endpoints
│   ├── core/
│   │   ├── config.py             # App configuration and settings via Pydantic
│   │   └── database.py           # PostgreSQL engine and session management
│   ├── models/                   # SQLAlchemy database models
│   ├── schemas/                  # Pydantic schemas / DTOs
│   └── main.py                   # FastAPI application initialization & routing
├── .env.example                  # Environment variable template
├── requirements.txt              # Python package dependencies
└── README.md
```

## Setup & Running Locally

### 1. Create and Activate Virtual Environment
```bash
cd backend
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 4. Run the Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Verify Endpoints
- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
