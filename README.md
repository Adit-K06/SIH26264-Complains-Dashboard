# AICTE Complaint Coordination Dashboard — SIH26264

> **Demo uses synthetic data. SLA values are placeholders, not official AICTE norms.**

A monitoring and coordination layer over existing AICTE Bureau/Cell systems. It does not replace them.

## Requirements

- Python 3.11 or 3.12
- Node.js and npm

## Local setup

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Create `backend/.env` with a SQLite URL, a private secret of at least 32 characters, and `APP_ENV=development`. Keep this file local.

```dotenv
DATABASE_URL=sqlite:///./aicte.db
SECRET_KEY=<generate-a-private-secret-of-at-least-32-characters>
APP_ENV=development
LLM_ENABLED=false
```

To generate a secret, run `python -c "import secrets; print(secrets.token_urlsafe(48))"` and paste its output as the `SECRET_KEY` value.

Seed the synthetic demo data and start the API:

```powershell
python -m app.seed
uvicorn app.main:app --reload
```

The API is available at **http://localhost:8000** and its docs at **http://localhost:8000/docs**.

### Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Vite serves the dashboard at **http://localhost:5173**.

## Demo accounts

Password for all demo accounts: `Demo@12345`

| Username | Role | Access |
|---|---|---|
| `admin` | ADMIN | Full access and demo clock |
| `senior` | SENIOR_MGMT | Read all and escalate |
| `rb_officer` | BUREAU_OFFICER | RB bureau |
| `pgrc_officer` | BUREAU_OFFICER | PGRC bureau |
| `regional_north` | REGIONAL_OFFICER | Northern region |

## Tests and evaluation

```powershell
cd backend
python -m pytest -v
python -m app.ai.evaluate
```

Frontend build:

```powershell
cd frontend
npm run build
```

## Data and limitations

All demo records are synthetic. No real AICTE complaint data is used. Bureau and region names are assumptions. SLA timelines are placeholders, not official AICTE norms. The dashboard monitors and coordinates work across existing systems.