.PHONY: api web test test-backend test-frontend seed

api:
	cd backend && python -m uvicorn app.main:app --reload

web:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	cd backend && python -m pytest -v

test-frontend:
	cd frontend && npm run build

seed:
	cd backend && python -m app.seed