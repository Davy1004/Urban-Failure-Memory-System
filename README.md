# Urban Failure Memory System — backend

Decision support for preventive municipal maintenance. Ranks a city's known
failure points by tonight's risk, flags locations becoming failures before
they reach the official register, and measures whether past interventions
worked.

Primary city: **Bengaluru** (BBMP). Demo city: **Delhi** (PWD list, no
ground truth).

This repository holds both halves of the system: the FastAPI backend at the
root, and the React dashboard in **`frontend/`** (its own npm project, with its
own README — read that before changing a screen; several presentation rules
there are results, not taste).

**For the evaluation demo, follow `docs/03-demo-runbook.md`, not this section.**
It is the cold-start sequence written to be executed literally, with the
failure modes and what to do about them.

## Quick start

```bash
# 1. Database (MySQL on host port 3307, not 3306 - see CLAUDE.md)
docker compose up -d
alembic upgrade head          # builds the schema, views included
# ...or load the canonical DDL directly. The charset flag is NOT optional:
# without it two column comments are stored double-encoded.
# docker exec -i ufms-mysql mysql --default-character-set=utf8mb4 #     -uroot -proot < ufms_schema.sql

# 2. Environment
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into SECRET_KEY

# 3. Run
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs

Health check: `curl http://127.0.0.1:8000/api/v1/health`

## Creating the first admin

`/auth/register` is admin-only, so bootstrap one directly:

```bash
python - <<'PY'
from app.db.session import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.enums import UserRole

db = SessionLocal()
db.add(User(
    name="Tanmay", email="admin@ufms.local",
    password_hash=hash_password("change-this-password"),
    role=UserRole.ADMIN, is_active=True,
))
db.commit()
print("admin created")
PY
```

Then `POST /api/v1/auth/login` with that email and password to get a token.

## Migrations

The schema ships as `ufms_schema.sql` (canonical DDL). Alembic is wired up
for changes after that baseline:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Layout

| Path | Purpose |
|---|---|
| `app/core/` | config, JWT + bcrypt, exception handlers, logging |
| `app/db/` | engine, session factory, declarative base |
| `app/models/` | 31 ORM models mirroring the SQL schema |
| `app/derived/` | the four dashboard computations; reconciled, not ingested |
| `app/schemas/` | Pydantic validation and response models |
| `app/repositories/` | data access layer |
| `app/services/` | business logic, owns transactions |
| `app/api/v1/` | routers |
| `app/middleware/` | request logging with correlation ids |

## Endpoints so far

| Method | Path | Auth |
|---|---|---|
| GET | `/api/v1/health` | none |
| POST | `/api/v1/auth/login` | none |
| POST | `/api/v1/auth/register` | admin |
| GET | `/api/v1/auth/me` | any |
| GET | `/api/v1/locations` | any |
| GET | `/api/v1/locations/{id}` | any |
| POST | `/api/v1/locations` | admin |
| PATCH | `/api/v1/locations/{id}` | admin |
| DELETE | `/api/v1/locations/{id}` | admin |
| GET | `/api/v1/index` | any |
| GET | `/api/v1/index/{ward}` | any |
| GET | `/api/v1/watchlist` | any |
| GET | `/api/v1/emerging` | any |
| GET | `/api/v1/allocation` | any |

The five dashboard endpoints are read-only for both roles and are what
`frontend/` consumes. Each carries its own caveats — `oracle_at_k`,
`random_at_k`, `ground_truth_available`, `retraction` — as **required** response
fields, so a screen cannot quietly drop the context a number needs.

Next: the memory engine and the model ladder M0-M3 — to demonstrate the
measured bound, not to beat it (see `docs/01-evaluation-rules.md`).

## Read `CLAUDE.md` first

It records the decisions behind this design — the framing, the frozen scope,
and the leakage and evaluation rules that keep the results valid.
