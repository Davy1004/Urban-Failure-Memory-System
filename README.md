# Urban Failure Memory System — backend

Decision support for preventive municipal maintenance. Ranks a city's known
failure points by tonight's risk, flags locations becoming failures before
they reach the official register, and measures whether past interventions
worked.

Primary city: **Bengaluru** (BBMP). Demo city: **Delhi** (PWD list, no
ground truth).

## Quick start

```bash
# 1. Database
docker compose up -d
docker exec -i ufms-mysql mysql -uroot -proot < ../ufms_schema.sql

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
| `app/models/` | 26 ORM models mirroring the SQL schema |
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

Next: ingestion (Open-Meteo, BBMP complaints, BBMP hotspot register), then
the memory engine and the nightly triage endpoint.

## Read `CLAUDE.md` first

It records the decisions behind this design — the framing, the frozen scope,
and the leakage and evaluation rules that keep the results valid.
