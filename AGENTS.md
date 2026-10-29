# AGENTS.md: SIH26264 AICTE Complaint Coordination Dashboard (READ FULLY BEFORE ANY CODE)

Monitoring and coordination layer over existing AICTE Bureau/Cell systems. It does NOT replace them.
Users are non-technical AICTE officers. Every screen must be understandable in 10 seconds.

## HARD RULES
1. NO Docker. Run natively: `uvicorn` for the API, `npm run dev` for the UI. SQLite file DB (`DATABASE_URL=sqlite:///./aicte.db`). Do not add Docker, Compose, nginx, Redis or Celery.
2. All data is SYNTHETIC (source='SYNTHETIC'). Show footer on every page: "Demo uses synthetic data. SLA values are placeholders, not official AICTE norms."
3. Never invent metrics. Precision/recall come only from `python -m app.ai.evaluate`.
4. Source of truth for enums, table names and columns: `backend/app/models/*.py` (already built and tested). Do NOT rename or add fields, statuses or enums without telling me first.
5. Backend enforces RBAC. Frontend only hides things.
6. `case_actions` is append-only: only INSERT, never UPDATE/DELETE. Every status change writes a case_actions row in the same transaction.
7. No external network calls at runtime (no CDN, no Google Fonts, no LLM). `LLM_ENABLED=false`.
8. One feature at a time. Run the test or the app before saying it works. Paste real output. Never claim something passed unless you ran it.
9. Do not commit .env or the .db file. Pin dependency versions.

## STACK
Backend: Python 3.11/3.12, FastAPI, Pydantic v2, SQLAlchemy 2, passlib+bcrypt (pin bcrypt==4.0.1), python-jose, rapidfuzz, scikit-learn. No Alembic needed: create tables with `Base.metadata.create_all`.
Frontend: React 18, Vite, TypeScript, Tailwind, react-router-dom, @tanstack/react-query, recharts, axios, lucide-react.

## DB NOTE
Models used Postgres JSONB. Use `sqlalchemy.JSON` instead. Keep every other column as is. Postgres-only things (trigram index, append-only trigger) are dropped; enforce append-only in code and add a test that proves no code path updates case_actions.

## API (prefix /api; errors {"error":{"code","message"}}; lists {"items","total","page","page_size"})
Auth: POST /auth/login, GET /auth/me
Institutions: GET /institutions (q, region_id, page), GET /institutions/{id}, GET /institutions/{id}/cases
Cases: GET /cases (q, institution_id, aicte_id, bureau_id, region_id, category_id, status, priority, from_date, to_date, beyond_sla, no_recent_action_days, linked, page, page_size), GET /cases/{id}, POST /cases, POST /cases/{id}/actions | /transfer | /escalate | /dispose | /reopen
Overlaps: GET /overlaps (tier, state), POST /overlaps/{id}/link (lead_bureau_id, note), POST /overlaps/{id}/dismiss, POST /overlaps/scan
Dashboard: GET /dashboard/summary, /dashboard/workload, /dashboard/ageing, /dashboard/trend
Alerts: GET /alerts, POST /alerts/{id}/read, POST /admin/demo/forward?days=N (ADMIN: runs the SLA check with a shifted clock)
Reports: GET /reports/{type}?format=csv|json  types: bureau, region, institution, ageing, disposal-rate, status, overlaps, monthly
Other: GET /admin/evaluation (reads docs/evaluation.json), GET /api/health

## WORKFLOW RULES
Allowed: PENDING->UNDER_PROCESS, UNDER_PROCESS->DISPOSED, any open->TRANSFERRED, any open->ESCALATED, DISPOSED->PENDING (reopen; remarks required else 422). Anything else 409. Open = not DISPOSED.
Single function `apply_transition(db, case, user, action_type, to_status, remarks)` is the only place that changes status.

## RBAC
BUREAU_OFFICER: read all; act only in own bureau. REGIONAL_OFFICER: act only for institutions in own region. SENIOR_MGMT: read all + escalate only. ADMIN: everything + demo clock. complainant_ref masked unless same bureau/region or ADMIN.

## OVERLAP ENGINE (backend/app/ai/)
Tier A: institution has open cases in >=2 distinct bureaus -> flag "Potential Overlapping Cases - Coordination Required".
Tier B: cross-bureau open pairs at the same institution. score = 0.45*text_sim + 0.30*category_match + 0.15*time_proximity + 0.10*ref_overlap. text_sim = cosine of TF-IDF (word 1-2 grams and char 3-5 grams, averaged). time_proximity = max(0, 1 - days_apart/90). Threshold constant OVERLAP_THRESHOLD, tuned only on the train split. Reason codes: HIGH_TEXT_SIMILARITY, SAME_CATEGORY, WITHIN_30_DAYS, SHARED_REFERENCE, SHARED_COMPLAINANT_REF, DIFFERENT_BUREAU.
Dismissed pairs are not re-raised unless a case summary or status changed after decided_at.
Resolver: exact AICTE ID, else RapidFuzz token_set_ratio after normalising (inst->institute, engg->engineering, tech->technology, coll->college, univ->university). >=0.92 auto, 0.75-0.92 needs review, below: unresolved.

## SLA (placeholders; label as such)
days_to_dispose 30, warn at 75%, reminder after 7 days no action, escalate 10 days after overdue. Alerts: DUE_SOON, OVERDUE, REMINDER, ESCALATION, OVERLAP; at most one per (case, type, day). Escalation also writes an ESCALATED case_actions row via apply_transition with actor = system user.

## SEED (deterministic, seed 42, `python -m app.seed`)
40 institutions (IDs SYN-xxxxx), ~300 cases over 12 months across RB, PGRC, APPROVAL, ACADEMIC, FINANCE; 12 planted overlap pairs (RB+PGRC, paraphrased, different case_nos); 15 hard negatives; 5 same-bureau near-duplicates; 8 messy institution names; labels in data/labels.csv. Users (password Demo@12345, demo only): admin, senior, rb_officer, pgrc_officer, regional_north. Include one institution that has a PGRC case but NO RB case, for the live demo.

## UX
Left sidebar: Dashboard, Cases, Institutions, Overlaps, Alerts, Reports, Evaluation. Navy/teal, white cards, status colours: Pending amber, Under process blue, Disposed green, Transferred purple, Escalated/overdue red. Every page: one-line helper text, loading, empty and error states. Header text on Overlap Center exactly: "Potential Overlapping Cases - Coordination Required". 1366px primary.

## OUT OF SCOPE (do not build)
Docker, attachments, PDF export, LLM/chatbot, Hindi UI, websockets, email/SMS, background worker container.

## PHASE HISTORY
- P0 scaffold done. P1 schema/models done (tests in backend/tests/test_schema.py were written for Postgres and will need adapting to SQLite).