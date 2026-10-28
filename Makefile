# Makefile — convenience targets for common dev tasks
.PHONY: up down build test test-backend test-frontend migrate seed logs shell-api shell-db

# ── Docker Compose ──────────────────────────────────────────
up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

# ── Tests ────────────────────────────────────────────────────
test: test-backend test-frontend

test-backend:
	cd backend && python -m pytest -v

test-frontend:
	cd frontend && npm run build

# ── Database ─────────────────────────────────────────────────
migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m app.seed

# ── Shell access ─────────────────────────────────────────────
shell-api:
	docker compose exec api bash

shell-db:
	docker compose exec db psql -U aicte aicte

# ── Backup ───────────────────────────────────────────────────
backup:
	docker compose exec db pg_dump -U aicte aicte > backup_$(shell date +%Y%m%d_%H%M%S).sql
