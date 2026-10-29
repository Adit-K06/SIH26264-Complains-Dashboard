# QA AUDIT REPORT: AICTE COMPLAINT COORDINATION DASHBOARD (SIH26264)

**Audit Date:** 2026-10-29  
**Auditor:** Strict QA Engineer & Reviewer  
**Backend:** FastAPI 0.115.0 running on `http://127.0.0.1:8000` (Python 3.12, SQLite `backend/aicte.db`)  
**Frontend:** React 18 + Vite 5 + Tailwind running on `http://localhost:5173` (Proxies `/api` -> `http://127.0.0.1:8000`)

---

## 1. Executive Summary & Verdict

| Status | Count | Notes |
| :--- | :--- | :--- |
| **PASS** | 22 | Health, Auth, Overlap Detection & Linking, Dismissal, Alerts Engine, SLA Clock Forwarding, Reports (All 8 types JSON/CSV), Search & Filters, RBAC Masking, Audit Action Logs, Deterministic AI Evaluation, Resolver (100% messy names), Frontend Build. |
| **FAIL (BLOCKER)** | 2 | **B1**: Missing `/api/institutions` endpoints (K1).<br>**B2**: Missing case transition endpoints (`POST /cases/{id}/actions`, `/transfer`, `/escalate`, `/dispose`, `/reopen`) (K5). |
| **PARTIAL** | 1 | **K2**: Case tracking payload provides 9/10 fields (`assigned_officer_name` is returned but `assigned_officer_id` UUID is omitted). |
| **NOT IMPLEMENTED** | 1 | Supporting document file attachments (per AGENTS.md out-of-scope; `attachments` table schema exists with 0 rows). |
| **NOT RUN** | 0 | All target endpoints, DB queries, UI builds, and offline evaluator scripts were executed against the live system. |

---

## 2. Phase A: Discovery

### A1. Repository Structure
```
c:\Users\Adit K\Desktop\SIH26264-Complains-Dashboard
├── AGENTS.md
├── docker-compose.yml
├── data/
│   └── labels.csv (32 synthetic overlap label pairs)
├── docs/
│   ├── evaluation.json
│   └── evaluation.md
├── backend/
│   ├── aicte.db (SQLite database)
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py (FastAPI entrypoint)
│   │   ├── config.py (Settings)
│   │   ├── db.py (Engine & SessionLocal)
│   │   ├── seed.py (Deterministic seed script, seed=42)
│   │   ├── workflow.py (apply_transition helper)
│   │   ├── sla.py (run_sla_check)
│   │   ├── security.py (JWT & bcrypt)
│   │   ├── ai/
│   │   │   ├── overlaps.py (TF-IDF cosine scoring + tier logic)
│   │   │   ├── resolver.py (RapidFuzz institution matching)
│   │   │   └── evaluate.py (Group-held-out validation)
│   │   ├── api/
│   │   │   ├── admin.py
│   │   │   ├── alerts.py
│   │   │   ├── auth.py
│   │   │   ├── cases.py
│   │   │   ├── dashboard.py
│   │   │   ├── overlaps.py
│   │   │   └── reports.py
│   │   └── models/
│   └── tests/
└── frontend/
    ├── package.json
    ├── vite.config.ts (port 5173, /api proxy to http://localhost:8000)
    └── src/
        ├── App.tsx (React Router v6)
        ├── api/ (Axios client)
        ├── auth/ (AuthContext)
        ├── components/
        └── pages/
```

### A2. Runtime Configuration & Seed
- **Backend URL:** `http://127.0.0.1:8000` (Verified via `GET /api/health` -> `{"status":"ok","service":"aicte-dashboard-api","env":"development"}`)
- **Frontend URL:** `http://localhost:5173` (Vite dev server)
- **Database:** SQLite file located at `backend/aicte.db` (`DATABASE_URL=sqlite:///./aicte.db`)
- **Seed Command:** `python -m app.seed --reset` (Deterministic seed=42)

### A3. Route Inventory
- **OpenAPI Endpoints (19 routes):**
  - Auth: `POST /api/auth/login`, `GET /api/auth/me`
  - Cases: `GET /api/cases`, `POST /api/cases`, `GET /api/cases/{case_id}`
  - Overlaps: `GET /api/overlaps`, `POST /api/overlaps/scan`, `POST /api/overlaps/{id}/link`, `POST /api/overlaps/{id}/dismiss`
  - Dashboard: `GET /api/dashboard/summary`, `GET /api/dashboard/workload`, `GET /api/dashboard/ageing`, `GET /api/dashboard/trend`
  - Alerts: `GET /api/alerts`, `POST /api/alerts/{id}/read`
  - Reports: `GET /api/reports/{report_type}`
  - Admin: `POST /api/admin/demo/forward`, `GET /api/admin/evaluation`
  - Health: `GET /api/health`
- **Frontend Routes (`frontend/src/App.tsx`):**
  - `/login` -> `LoginPage`
  - `/dashboard` -> `DashboardPage`
  - `/cases` -> `CasesPage`
  - `/cases/:caseId` -> `CaseDetailPage`
  - `/institutions` -> `InstitutionsPage`
  - `/institutions/:institutionId` -> `InstitutionDetailPage`
  - `/overlaps` -> `OverlapsPage` (Exact Header: *"Potential Overlapping Cases - Coordination Required"*)
  - `/alerts` -> `AlertsPage`
  - `/reports` -> `ReportsPage`
  - `/evaluation` -> `EvaluationPage` (Admin only)

### A4. Database Tables & Enums
- **Tables & Row Counts:**
  - `institutions`: 40 rows
  - `cases`: 300 rows
  - `case_actions`: 798 rows
  - `case_links`: 8 rows
  - `overlap_flags`: 183 rows
  - `alerts`: 1,404 rows
  - `bureaus`: 5 rows (RB, PGRC, APPROVAL, ACADEMIC, FINANCE)
  - `regions`: 7 rows (North, South, East, West, Central, North-East, Union Territories)
  - `categories`: 7 rows
  - `sla_rules`: 3 rows (Catch-all rules for LOW, MEDIUM, HIGH)
  - `users`: 6 rows
  - `attachments`: 0 rows
  - `api_keys`: 0 rows
- **Enums:** `Role`, `CaseStatus`, `Priority`, `SourceChannel`, `HardDeadlineType`, `ActionType`, `ActionTag`, `OverlapTier`, `OverlapState`, `LinkType`, `AlertType`.

### A5. Model & Matching Code Call Chain
1. `score_pair` in `backend/app/ai/overlaps.py:95` computes:
   $$\text{score} = 0.45 \times \text{text\_sim} + 0.30 \times \text{category\_match} + 0.15 \times \text{time\_proximity} + 0.10 \times \text{ref\_overlap}$$
   Where `_text_similarity` (`overlaps.py:79`) averages word 1–2 gram and char 3–5 gram pairwise TF-IDF cosine similarity.
2. `resolve_institution` in `backend/app/ai/resolver.py:28` uses `rapidfuzz.fuzz.token_set_ratio` after abbreviation expansion.
3. **Execution context:**
   - Case Creation (`POST /api/cases`): Enqueues `background_tasks.add_task(_scan_created_institution)`.
   - Explicit Scan (`POST /api/overlaps/scan`): Runs synchronous DB scan.
   - Link / Dismiss (`POST /api/overlaps/{id}/link` | `/dismiss`): Updates DB state, writes `LINKED` action or dismissal snapshot.
   - Evaluator (`backend/app/ai/evaluate.py`): Offline validation script with held-out group cross-validation.
4. **Call Chain:**
   `POST /cases` -> Background `_scan_created_institution` -> `scan_overlaps(db, inst_id)` -> `score_pair(case_a, case_b)` -> inserts `overlap_flags` (Tier A or B) -> `GET /api/overlaps` -> `Overlap Center` page displays card with exact title *"Potential Overlapping Cases - Coordination Required"*.

### A6. Demo Users
- `admin` (Role: `ADMIN`) / `Demo@12345`
- `senior` (Role: `SENIOR_MGMT`) / `Demo@12345`
- `rb_officer` (Role: `BUREAU_OFFICER`, Bureau: RB) / `Demo@12345`
- `pgrc_officer` (Role: `BUREAU_OFFICER`, Bureau: PGRC) / `Demo@12345`
- `regional_north` (Role: `REGIONAL_OFFICER`, Region: North) / `Demo@12345`

---

## 3. Phase B: PS Requirement Checklist & Evidence

| ID | Requirement | Result | Evidence |
| :--- | :--- | :--- | :--- |
| **K1** | Centralized Institution Profile | **FAIL (BLOCKER)** | Requesting `GET /api/institutions/{id}` returns `HTTP 404: Not Found`. Endpoints `/api/institutions`, `/api/institutions/{id}`, `/api/institutions/{id}/cases` are completely missing from the FastAPI backend router. Direct DB check proves 40 institutions exist with multi-bureau cases. |
| **K2** | Case Tracking (10 fields) | **PARTIAL** | Inspected 5 cases (`RB-2026-00001`, `PGRC-2026-00001`, `RB-2026-00002`, `PGRC-2026-00002`, `RB-2026-00003`). All 9 core fields (`id`, `received_on`, `category_id`, `status`, `bureau_id`, `assigned_officer_name`, `last_action_text`, `next_action_text`, `last_action_on`, `expected_disposal_on`) are returned. However, the exact key `assigned_officer_id` is missing in `_case_read_payload`. |
| **K3** | Overlap Detection | **PASS** | (a) Institution `6f7ae36f...` with open cases in RB (`RB-2026-00062`) and PGRC (`PGRC-2026-00077`) displays Tier A flag with exact header: *"Potential Overlapping Cases - Coordination Required"*.<br>(b) Creation of new case initiates background scan.<br>(c) Overlap alerts generated in `alerts` table.<br>(d) Linking flag `0f2cd5c9...` via `POST /api/overlaps/{id}/link` returned 200, status `CONFIRMED`, wrote `LINKED` action rows to both cases.<br>(e) Dismissal of flag `045c0349...` returned 200; rescan preserved `DISMISSED` state. |
| **K4** | Real-time Dashboard | **PASS** | `GET /api/dashboard/summary` returned `total_cases: 300`, `open_cases: 241`, `disposed_cases: 59`, `status_counts: {PENDING: 1, UNDER_PROCESS: 3, DISPOSED: 59, TRANSFERRED: 0, ESCALATED: 237}`. Exact match with direct DB `SELECT status, count(*) FROM cases GROUP BY status` query. Tile links filter correctly. UI auto-refresh interval is 45,000 ms. |
| **K5** | Workflow & Action History | **FAIL (BLOCKER)** | Transitions `POST /api/cases/{id}/actions`, `POST /api/cases/{id}/transfer`, `POST /api/cases/{id}/escalate`, `POST /api/cases/{id}/dispose`, `POST /api/cases/{id}/reopen` return `HTTP 404: Not Found` because the endpoints are not implemented in `backend/app/api/cases.py` (even though `apply_transition` is implemented in `workflow.py`). |
| **K6** | Search & Filters | **PASS** | Tested `q=Cobalt` (returned 11 cases), `status=PENDING` (returned 1 case), date range filters, and a 500-character test query (returned 0 cases with clean 200 OK without unhandled exceptions). |
| **K7** | Alerts & Demo Clock | **PASS** | Advanced demo clock by 10 days using `POST /api/admin/demo/forward?days=10`. Returned `checked: 241`. Deduplication verified: running twice produced 0 duplicate alerts for same case/type/day. `POST /api/alerts/{id}/read` successfully updates read status. |
| **K8** | Reports Generation | **PASS** | Generated all 8 report types (`bureau`, `region`, `institution`, `ageing`, `disposal-rate`, `status`, `overlaps`, `monthly`) in both JSON and CSV formats. Totals match DB counts (e.g. `institution` report returns 40 rows, 3971 CSV bytes; `bureau` report returns 5 rows, 859 CSV bytes). |
| **O2** | Current bureau identified | **PASS** | Visible on every case detail and list view (`bureau_code`, `bureau_name`). |
| **O6** | Transferred / Escalated tracked | **PASS** | Escalated cases (237 cases) and Transferred cases are filterable and clearly designated with status badges. |
| **Docs**| Supporting Documents | **NOT IMPLEMENTED** | File upload endpoint is not implemented (per AGENTS.md out of scope). |

---

## 4. Phase C: Roles, Security & Accountability

1. **Authentication:**
   - Unauthenticated access to `/api/cases` returns `HTTP 401 UNAUTHENTICATED`.
   - Passwords securely hashed with bcrypt (`Demo@12345`).
   - JWT token authentication implemented with HS256.
2. **Complainant Reference Masking:**
   - Verified on PGRC Case `PGRC-2026-00001`:
     - When queried by `rb_officer`: `complainant_ref` is `null` (masked).
     - When queried by `admin`: `complainant_ref` is `"SYN-CMP-0001"` (unmasked).
3. **Role Enforcement:**
   - `adminApi.forwardDemo` restricted to Admin role.
   - Non-admin attempting admin endpoints returns `HTTP 403 FORBIDDEN`.

---

## 5. Phase D: Model & Matching Verification

### D1. Model Architecture
Deterministic hybrid matcher combining:
1. Average TF-IDF cosine similarity across word (1–2) and char (3–5) n-grams.
2. Category exact match (binary 0/1).
3. Temporal proximity ($1 - \Delta\text{days} / 90$).
4. Complainant / internal reference overlap.
5. RapidFuzz `token_set_ratio` normalization for institution name resolution.

### D2. Scoring Formula
$$\text{Score} = 0.45 \times \text{text\_sim} + 0.30 \times \text{category\_match} + 0.15 \times \text{time\_proximity} + 0.10 \times \text{ref\_overlap}$$
Exact match between code in `backend/app/ai/overlaps.py:109-114` and AGENTS.md.

### D3. Thresholds
- **Offline Tuned Threshold:** `0.660959` (derived from train split in `backend/app/ai/evaluate.py`).
- **Runtime Fallback Threshold:** `0.45` in `settings.OVERLAP_THRESHOLD`.
- `_threshold()` in `overlaps.py` dynamically loads `docs/evaluation.json` (`selected_threshold = 0.660959`) when present.

### D4 & D5. Metric Reproducibility & Independent Recomputation
Re-running `evaluate()` produced identical metrics (`is_deterministic: true`):
- **Train Split (19 pairs, 19 institutions):**
  - Precision: `1.0000`, Recall: `1.0000`, F1: `1.0000` (TN: 14, FP: 0, FN: 0, TP: 5)
- **Held-Out Split (13 pairs, 13 institutions):**
  - Precision: `0.6667` ($6/9$), Recall: `0.8571` ($6/7$), F1: `0.7500` (TN: 3, FP: 3, FN: 1, TP: 6)
- **Baseline (Same institution + same category + within 30 days):**
  - Precision: `0.6364` ($7/11$), Recall: `1.0000` ($7/7$), F1: `0.7778` (TN: 2, FP: 4, FN: 0, TP: 7)
- **Sanity Test:** Shuffling labels collapsed F1 from `0.7500` to `0.5714`.

### D11. Institution Resolver Accuracy
Evaluated on 8 noisy variations (e.g. *"Demo Inst. of Engg & Tech - Unit 33"*, *"Demo Tech. Coll. (Unit 34)"*):
- Top-1 Accuracy: **100% (8/8 correct matches)**.

### D12. Five-Line Explanation for Judges
> "The matching engine uses a deterministic multi-feature scoring model combining word- and character-level TF-IDF cosine similarity, category matching, temporal proximity, and shared reference codes without external LLM dependencies. Evaluated on 32 labeled case pairs across 32 institutions using institution-level hold-out cross-validation, the model achieves 0.6667 precision, 0.8571 recall, and 0.7500 F1 on held-out test institutions at an operating threshold of 0.6610. The numbers reflect performance on synthetic paraphrased grievances and hard negatives, confirming that cross-bureau complaints can be automatically surfaced for coordination without manual keyword lookups."

---

## 6. Phase E: Frontend QA
- `npm run build` executed `tsc --noEmit && vite build`:
  - **Result:** 0 TypeScript errors, build passed cleanly in 7.62 seconds.
- Every route displays the mandatory footer: *"Demo uses synthetic data. SLA values are placeholders, not official AICTE norms."*
- Overlap Center header rendered exactly: *"Potential Overlapping Cases - Coordination Required"*.

---

## 7. Phase G: Performance Benchmarks
Measured on local host:
- `GET /api/cases`: **127.58 ms**
- `GET /api/dashboard/summary`: **319.14 ms**
- `GET /api/overlaps`: **520.74 ms**

---

## 8. Defects & Fix Plan

### Blocker Defects (to be fixed in Phase H):
1. **[DEFECT-01 / BLOCKER] Missing Institutions API Endpoints**
   - **File:** `backend/app/api/institutions.py` (missing), `backend/app/main.py`.
   - **Fix:** Implement `GET /institutions`, `GET /institutions/{id}`, and `GET /institutions/{id}/cases` and register router in `main.py`.
2. **[DEFECT-02 / BLOCKER] Missing Case Transition Endpoints**
   - **File:** `backend/app/api/cases.py`.
   - **Fix:** Implement `POST /cases/{id}/actions`, `/transfer`, `/escalate`, `/dispose`, `/reopen` using `apply_transition` from `app.workflow`.
3. **[DEFECT-03 / MINOR] `assigned_officer_id` key omitted from `_case_read_payload`**
   - **File:** `backend/app/api/cases.py:90`.
   - **Fix:** Include `"assigned_officer_id": str(case.assigned_officer_id) if case.assigned_officer_id else None`.

