# SIH26264 — Integrated Complaint Monitoring Dashboard (AICTE)

> **All data in this project is SYNTHETIC. SLA values are PLACEHOLDERS, not official AICTE norms.**

A full-stack web application for monitoring and tracking institution-related complaint cases across AICTE Bureaus/Cells. It is a coordination layer over existing Bureau systems — it does **not** replace them.

---

## 🏗️ Architecture

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS v4, TanStack Query/Table, Recharts, React Router v7 |
| **Backend API** | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 16 |
| **AI/ML** | RapidFuzz (fuzzy institution matching), scikit-learn TF-IDF (complaint overlap detection) |
| **Background Worker** | APScheduler |
| **Infrastructure** | Docker, Docker Compose, nginx |

---

## 🚀 Quick Start (Docker — Recommended)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Git

### 1. Clone & Setup
```bash
git clone <your-repo-url>
cd sih26264-complaint-dashboard
cp .env.example .env
```

> **Optional:** Edit `.env` to set a strong `JWT_SECRET` for production. The defaults are development-only.

### 2. Start All Services
```bash
docker compose up --build -d
```

This starts:
- **PostgreSQL 16** database on port 5432
- **FastAPI** backend API on port 8000
- **APScheduler** background worker
- **React/nginx** frontend on port 80

### 3. Run Database Migrations + Seed Data
```bash
# Run schema migrations
docker compose exec api alembic upgrade head

# Seed demo users (admin, managers, officers)
docker compose exec api python -m app.seed

# Seed synthetic institution + complaint data (AI module)
docker compose exec api python -m app.ai.seed --reset
```

### 4. Open the App
- **Dashboard:** http://localhost
- **API docs (Swagger):** http://localhost:8000/docs
- **API health:** http://localhost:8000/api/v1/health

---

## 🔐 Demo Credentials

| Email | Password | Role |
|---|---|---|
| `admin@demo.local` | `admin123` | ADMIN |
| `mgmt@demo.local` | `mgmt123` | SENIOR_MGMT |
| `rb.officer@demo.local` | `officer123` | BUREAU_OFFICER (RB) |
| `pgrc.officer@demo.local` | `officer123` | BUREAU_OFFICER (PGRC) |
| `regional@demo.local` | `officer123` | REGIONAL_OFFICER (Northern) |

---

## 💻 Local Development (without Docker)

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # Mac/Linux

pip install -r requirements.txt

# Needs a running PostgreSQL. Update DATABASE_URL in .env
alembic upgrade head
python -m app.seed
python -m app.ai.seed --reset
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
# .env.local already has VITE_USE_MOCKS=false to use real backend
npm run dev
```

Frontend dev server runs on http://localhost:5173. API requests are proxied to `http://localhost:8000`.

> To use mock data instead of a real backend: set `VITE_USE_MOCKS=true` in `frontend/.env.local`.

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### AI/ML Evaluation
```bash
# Inside Docker container:
docker compose exec api python -m app.ai.evaluate
```

---

## 📁 Project Structure

```
sih26264-complaint-dashboard/
├── backend/               # FastAPI application + AI/ML modules
│   ├── app/
│   │   ├── api/           # REST API routers (auto-mounted)
│   │   ├── ai/            # Institution resolver + overlap detector
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── worker/        # APScheduler background tasks
│   │   ├── main.py        # FastAPI app entry point
│   │   ├── auth.py        # JWT auth + RBAC helpers
│   │   ├── config.py      # Pydantic settings
│   │   ├── database.py    # SQLAlchemy session
│   │   ├── security.py    # Password hashing + JWT
│   │   └── seed.py        # Demo user seeder
│   ├── alembic/           # Database migrations
│   ├── tests/             # pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/              # React + Vite application
│   ├── src/
│   │   ├── api/           # API client + type definitions + mocks
│   │   ├── components/    # Reusable React components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── lib/           # Utility functions
│   │   └── pages/         # Page-level components
│   ├── Dockerfile         # Multi-stage build (Node → nginx)
│   ├── nginx.conf         # nginx proxy + SPA fallback config
│   └── package.json
├── data/                  # Synthetic CSV datasets
├── docs/                  # AI evaluation reports
├── docker-compose.yml     # All services
├── .env.example           # Environment variable template
├── .gitignore
└── README.md
```

---

## 🤖 AI/ML Features

### Institution Resolver (`app.ai.institution_resolver`)
- **Exact AICTE ID match** → confidence 1.0
- **Fuzzy name matching** (RapidFuzz) → auto-match ≥0.92, human review 0.75–0.92
- Handles abbreviations (inst/instt, engg, tech, coll, univ, govt)

### Overlap Detector (`app.ai.overlap`)
- **Tier A:** Institution with open cases in ≥2 distinct bureaus → coordination alert
- **Tier B:** Pairwise complaint similarity scoring:
  - Text similarity: 45% (TF-IDF cosine, word + char n-grams)
  - Category match: 30%
  - Time proximity: 15%
  - Reference/complainant overlap: 10%
  - Threshold: 0.40 (configurable)

---

## 🔧 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | `sih` | Database user |
| `POSTGRES_PASSWORD` | `sihpass` | Database password (**change in production**) |
| `POSTGRES_DB` | `sih` | Database name |
| `DATABASE_URL` | `postgresql+psycopg://sih:sihpass@db:5432/sih` | Full connection string |
| `JWT_SECRET` | `change-me` | JWT signing secret (**MUST change in production**) |
| `JWT_ACCESS_MINUTES` | `30` | Access token lifetime |
| `JWT_REFRESH_DAYS` | `7` | Refresh token lifetime |
| `CORS_ORIGINS` | `http://localhost,...` | Allowed CORS origins |
| `STORAGE_DIR` | `/data/uploads` | File upload storage path |

---

## 📋 API Endpoints

| Category | Endpoints |
|---|---|
| Auth | `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` |
| Cases | `GET/POST /cases`, `GET/PATCH /cases/{id}`, transitions: transfer, escalate, dispose, reopen |
| Institutions | `GET /institutions`, `GET /institutions/{id}`, `GET /institutions/resolve` |
| Overlaps | `GET /overlaps`, `POST /overlaps/scan`, `POST /overlaps/{id}/link`, `POST /overlaps/{id}/dismiss` |
| Dashboard | `GET /dashboard/summary`, `/dashboard/workload`, `/dashboard/ageing` |
| Reports | `GET /reports/{type}?format=csv|json|pdf` |
| Alerts | `GET /alerts`, `POST /alerts/{id}/read` |
| Import | `POST /ingest/cases` (API key), `POST /import/cases-csv` |
| Admin | `GET /admin/sla-rules`, `PUT /admin/sla-rules/{id}`, `GET /admin/users`, `GET /admin/evaluation` |

Full interactive docs: http://localhost:8000/docs

---

## ⚠️ Disclaimer

- All institution names, complaint data, and case numbers are **entirely synthetic** and generated for demonstration purposes only.
- SLA values are **placeholders** and do not represent official AICTE norms or policies.
- This application does **not** connect to any real AICTE systems.
