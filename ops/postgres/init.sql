-- Enable pg_trgm extension for fuzzy institution name search
-- (Alembic migrations run after this, so it's available)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
