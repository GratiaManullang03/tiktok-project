# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Personal (single-user, no auth) tool for TikTok Shop product research. Pipeline: scrape product data → compute a deterministic score → optionally run an LLM analysis on a product. FastAPI backend, PostgreSQL (Neon, external — no local Postgres container), raw SQL via psycopg2 (no ORM), Clean Architecture layering (api → services → repositories → schemas). Repo is private; commit messages/PRs can be in Indonesian or English, follow existing style.

## Commands

```bash
# Setup (Postgres is external/Neon — no local DB container)
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # fill in PGHOST/PGDATABASE/PGUSER/PGPASSWORD, GROQ_API_KEY
alembic upgrade head               # create "tiktok" schema + tables
uvicorn app.main:app --reload --port 8000

# Docker alternative
docker-compose up --build
docker-compose exec app alembic upgrade head

# Tests (CI runs this on every push/PR to main; no real DB/API keys needed —
# tests/conftest.py sets dummy env vars, external calls are mocked)
pytest
pytest tests/test_scoring.py::test_name   # single test

# Migrations — hand-written, Laravel-style (no autogenerate, no ORM models to diff)
alembic revision -m "add xyz column"      # ~ php artisan make:migration
alembic upgrade head                      # ~ php artisan migrate
alembic downgrade -1                      # ~ php artisan migrate:rollback

# Rescrape past keywords for fresh snapshots (schedule ~daily; see script docstring)
python scripts/rescrape.py [keyword ...] [--limit N]   # default limit: keyword's past max (tsj_limit)

# Refresh the Groq model catalog snapshot used for GROQ_MODEL validation
python scripts/fetch_groq_models.py
```

## Architecture

**Layering**: `app/api/v1/endpoints/` (FastAPI routes) → `app/services/` (business logic) → `app/repositories/` (raw SQL via psycopg2) → Postgres. `app/schemas/` holds Pydantic request/response models, kept separate from repository dict rows (`RealDictRow`).

**Transaction ownership**: repositories (`app/repositories/*.py`, all subclass `BaseRepository`) never commit or rollback — every method just executes SQL. The caller (a service function or endpoint) owns the transaction boundary and must explicitly `commit()` after all steps succeed or `rollback()` on the first failure. Multi-step writes (scrape → upsert product → save metric → compute score) are wrapped in one transaction for atomicity. See `app/services/pipeline.py` for the reference pattern.

**Pipeline flow** (`app/services/pipeline.py`):
1. `run_scrape_job` — plain sync `def` background task (FastAPI runs it in a threadpool, so blocking psycopg2/httpx calls don't stall the event loop) (FastAPI `BackgroundTasks`, no Celery/Redis) that runs a scraper, upserts each product by `mp_external_id`, saves a metric snapshot, and scores the product, all per-product-atomic; job progress/result lives in `trx_scrape_job` (`app/repositories/scrape_job.py`), not a queue system.
2. `score_product` — deterministic, LLM-free scoring from the three most recent metric snapshots (`app/services/scoring.py`, `ProductScoringService`). `hpm_units_sold` is a *lifetime* total, so velocity = units-sold delta per day between snapshots (`_units_per_day`), and growth = that velocity vs. the previous interval's. Snapshots < `MIN_SNAPSHOT_GAP` (20h) apart are skipped (`_spaced_snapshots`) — a product found under two keywords in one run gets two near-identical snapshots. So velocity needs 2 spaced snapshots and growth needs 3; before that they score 0. That's why `scripts/rescrape.py` exists: run it ~daily via cron. Competition = log-scaled total Tokopedia search results for the keyword (`hpm_competitor_count`, a per-keyword value, so the minimum across recent snapshots is used); rating is rescaled 4.0–5.0 → 0–100. Weights come from `SCORE_WEIGHT_*` env vars and must sum to 1.0 (enforced in `Settings`).
3. `analyze_product` — synchronous call to Groq (`app/services/llm_analysis.py`) using the latest score breakdown; computes a fresh score first if none exists.

**Scraper** (`app/services/scrapers/`): `TokopediaScraper` is the only implementation — calls Tokopedia's public `SearchProductV5Query` GraphQL endpoint directly via `httpx` (no browser, no auth, no API key). Data source is Tokopedia rather than `shop.tiktok.com` because the latter puts a slide-captcha in front of any anonymous visit and has no public search route at all; Tokopedia is a valid stand-in for TikTok Shop Indonesia research since the two catalogs merged in 2023 (each product in the response still carries a `ttsProductID`). `BaseScraper.search_products()` must return a list of `RawProduct` (the common normalized shape, see `base.py`); the pipeline consumes only that shape, so it's still the extension point if another source is ever added. Sold-count comes only from the exact `stock.sold` field — deliberately no fallback to the rounded `"10rb+ terjual"` label, because mixing exact and rounded counts across snapshots corrupts the velocity delta. GraphQL rejects the whole query if any requested field disappears, so a sudden "Tokopedia search returned no data" job failure means the query in `tokopedia_scraper.py` needs a field removed. `header.totalData` (total search results) becomes each product's `competitor_count`. The search API exposes no review count, commission, or video count — don't add columns for them expecting data.

**Soft delete**: `mst_product` uses `is_deleted`/`deleted_at` instead of hard delete, because it's the parent of `his_product_score` and `his_product_analysis` — hard delete would orphan research history. `ProductRepository.get()` overrides the base to filter `is_deleted = FALSE`; `get_by_external_id()` intentionally does not (used for upsert dedup regardless of delete state).

**No `created_by`/`updated_by`/`deleted_by`** anywhere — deliberate deviation from `docs/ERDRULES.md`, since this is a single-user tool with no real actor to attribute writes to.

**DB access**: `app/db/session.py` has two paths — `get_db()` (FastAPI dependency, request-scoped) and `get_connection()` (used by code that outlives the request, e.g. the background scrape job). Alembic itself uses SQLAlchemy internally purely as a migration-tooling detail; the application query layer never uses SQLAlchemy/ORM.

**Schema**: all tables live in the Postgres schema `tiktok`, with no `search_path` set, so every raw SQL query must schema-qualify tables (`tiktok.mst_product`, etc.; each repository keeps this in a `TABLE` constant). Migrations live in `migrations/versions/` (not the Alembic default `alembic/`).

**Naming convention** (`docs/ERDRULES.md`): tables are prefixed by kind (`mst_` master, `his_` history, `trx_` transaction); primary keys are `<table_abbreviation>_id`; foreign keys are `<owning_table_abbreviation>_<referenced_pk>`. Repository column names mirror these prefixes directly (e.g. `hps_total_score`, `hpm_units_sold`).

**API response envelope** (`app/schemas/common.py`): every endpoint returns `DataResponse[T]` (`{success, message, data}`) or, for collection endpoints only (`GET /products`, `GET /scrape/jobs`), `PaginationResponse[T]` (`{success, message, data, pagination}`) via `PaginationResponse.build(...)`. Single-resource GETs are never paginated. On `PUT`/`PATCH` for a resource, provenance/identity fields (e.g. `mp_id`, `mp_external_id`, `mp_source`, `mp_last_scraped_at`, `created_at`) are excluded from the request schema, not just ignored — see `ProductReplace`/`ProductPatch` in `app/schemas/product.py`.

**Config** (`app/core/config.py`): a single `pydantic-settings` `Settings` object (`settings`), loaded from `.env`. `GROQ_MODEL` must support `json_mode` — cross-check against `docs/models.json` (refreshed via `scripts/fetch_groq_models.py`).

`problem.md` is unrelated to the app (personal NVIDIA/Ubuntu troubleshooting notes). Ignore it.
