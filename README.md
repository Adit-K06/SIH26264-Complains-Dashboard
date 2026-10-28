# AICTE Complaint Coordination Dashboard — SIH26264

> **Demo uses synthetic data. SLA values are placeholders, not official AICTE norms.**

Integrated Dashboard for Monitoring and Tracking Institution-Related Complaint Cases Across AICTE Bureaus/Cells.

---

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Build and start all services (db + api + worker + web)
docker compose up --build

# 3. Open browser at http://localhost
```

The dashboard is available at **http://localhost** (port 80).  
API docs available at **http://localhost/api/docs**.

---

## Demo Credentials

> **Password for all demo accounts: `Demo@12345`**

| Username | Role | Access |
|---|---|---|
| `admin` | ADMIN | Full access + admin panel |
| `senior` | SENIOR_MGMT | Read all + escalate |
| `rb_officer` | BUREAU_OFFICER | RB bureau only |
| `pgrc_officer` | BUREAU_OFFICER | PGRC bureau only |
| `regional_north` | REGIONAL_OFFICER | Northern region only |

*(Accounts seeded in P2. Seed command: `docker compose exec api python -m app.seed`)*

---

## Architecture

```
http://localhost (port 80)
└── nginx (web container)
    ├── /          → React SPA (built from frontend/)
    └── /api/      → FastAPI backend (api container, port 8000)
                       └── PostgreSQL 16 (db container, port 5432)
                       └── APScheduler worker (worker container)
```

## Services

| Service | Container | Port |
|---|---|---|
| Frontend (React/nginx) | `web` | 80 |
| Backend (FastAPI) | `api` | 8000 |
| Worker (APScheduler) | `worker` | — |
| Database (PostgreSQL 16) | `db` | 5432 |

---

## Development

### Backend (local, without Docker)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run tests
python -m pytest

# Start API server (requires PostgreSQL running)
uvicorn app.main:app --reload
```

### Frontend (local, without Docker)

```bash
cd frontend
npm install
npm run dev    # starts at http://localhost:5173
```

---

## Running Tests

```bash
# Backend unit + integration tests
cd backend && python -m pytest -v

# Overlap evaluation (P7 onwards)
cd backend && python -m app.ai.evaluate

# Frontend E2E (Playwright, P16 onwards)
cd frontend && npx playwright test
```

---

## Phase Status

| Phase | Description | Status |
|---|---|---|
| P0 | Monorepo, Docker Compose, Health, CI | ✅ Done |
| P1 | Schema + Alembic migrations | ⏳ Next |
| P2 | Auth + RBAC | ⏳ Pending |
| P3–P17 | See AGENTS.md | ⏳ Pending |

---

## Limitations & Disclaimers

- All data is **synthetic** (generated with seed 42). No real AICTE complaint data is used.
- Bureau names (RB, PGRC, APPROVAL, ACADEMIC, FINANCE) and region names are **assumptions**.
- SLA timelines (21-day CPGRAMS, 30-day RTI) are **placeholder defaults**, not official AICTE norms.
- This system is a **monitoring/coordination layer** — it does not replace existing bureau systems.
- AI features (feature flag `LLM_ENABLED=true`) generate **draft suggestions only**; all decisions remain with officers.

---

## Backup

```bash
# Backup PostgreSQL data
docker compose exec db pg_dump -U aicte aicte > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T db psql -U aicte aicte < backup_20260101.sql
```
