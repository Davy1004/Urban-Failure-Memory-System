# UFMS — project context for Claude

Read this before making changes. It records decisions already taken and
settled; do not relitigate them without being asked.

## Current status — read this first

**Phase 0: COMPLETE and verified against a live database (7 Sep 2026).**
Schema (26 tables, 3 views), SQLAlchemy models matching it exactly, JWT +
bcrypt auth, repository/service layers, exception handling, request logging,
health check, Alembic wired up.

First real run is done: MySQL 8.0 booted via docker compose, `ufms_schema.sql`
loaded (26 tables + 3 views), venv built on Python 3.12, uvicorn served `/docs`
and `/api/v1/health` returned `"database": "reachable"`.
`tests/test_security.py` — 5 passed. Model metadata was diffed against the live
database: table sets match exactly, no column drift.

**Phase 1: IN PROGRESS.**

Done:
- `app/ingestion/base.py` — `ingestion_run` context manager (opens/closes an
  `ingestion_runs` row, marks failed runs loudly), `upsert_chunk` for MySQL
  INSERT ... ON DUPLICATE KEY UPDATE, `resolve_city`.
- `app/ingestion/open_meteo.py` — ERA5 hourly loader. 3x3 grid of cells per
  city at 0.2 degrees, chunked by 2-year windows, exponential backoff on 429,
  clamps the end date for the ~6 day archive lag. Idempotent.
- `app/ingestion/weather_daily.py` — daily aggregation into `weather_daily`.
  `rain_percentile` and `return_period_yrs` use an expanding window over
  strictly prior dates; `tests/test_weather_daily.py` pins that against
  regression. NULL below 365 days of history rather than a guess.
- `app/ingestion/cli.py` — `weather`, `weather-daily`, `status` subcommands.
- **Bengaluru weather is loaded**: 512,568 hourly rows over 9 ERA5 cells,
  2019-01-01..2025-06-30, aggregated to 21,357 cell-days.
- `docs/02-data-profile.md` — profile of the raw BBMP files. **Read §10 and
  §12 before writing the complaint loader.**
- `data/reference/ward_crosswalk.csv` + `app/ingestion/ward_crosswalk.py` —
  all 198 complaint ward names mapped to a BBMP ward number, polygon centroid,
  zone and area, off the 198-ward `bbmp_ward_map_2015.kml`. 0 unresolved.
- `app/ingestion/bbmp_wards.py` — 198 ward centroids + 398 register hotspot
  points into `locations`, each with its nearest ERA5 `cell_id`. The three
  register layers are loaded unmerged.
- **Weather is ECMWF-IFS (~9 km), not ERA5.** `--model ecmwf_ifs` is the CLI
  default; IFS resolves BBMP into 14 cells against ERA5's 3. `weather_cells`
  1-9 are ERA5, 10-23 are IFS.
- **Rainfall resolution is settled, and it is not the limit** (profile §17).
  Tripling resolution moves no figure (chi2 p = 0.877). **§17.4: a
  weather-only ranking scores 5.63% against a 4.80% random baseline, while
  memory alone reaches 14.08% and the ceiling is 37.72%.** Weather alone ranks
  at chance. Expect M1 to score ~5% - that is the predicted result, not a bug.
- **KSNDMC gauges are a dead end for now** (profile §18): 131 gauge locations
  inside BBMP, median 0.95 km per ward, but only 5 report to the national
  portal and only from Aug 2023. RTI, not a download.
- **THE HEADROOM IS NOT REACHABLE** (profile §19). A ward-level ranking fitted
  with perfect foresight scores 15.66% against the honest 14.08%, so only
  **1.6 of the 23.6 points (6.7%) is ward-level at all**; 93.3% is within-ward
  temporal variation. Consecutive rain nights' event vectors correlate at
  0.090. Terrain, elevation, and the prescribed `conditional_rate_at_band` /
  `excess_over_city` interactions were all built and tested - **every one is
  worse than prior event count alone**. Build the ladder to demonstrate the
  bound, not to beat it. **Proof One needs restating** - see
  `docs/01-evaluation-rules.md`.
- **Never report a pooled AUC for triage.** Pooled 0.749 vs within-night 0.737,
  and prior count alone also gives 0.737. Rainfall carries 74-100% of its
  variance between nights; precision@k only compares wards within one night.
- **Proof One is RESTATED** (`docs/01-evaluation-rules.md`). We no longer claim
  to beat the static list. The deliverable is the ceiling itself: *we establish
  the predictability ceiling of complaint-derived urban failure triage and
  locate where it binds.*
- **Magnitude is a weak secondary output** (profile §20). Weather cannot predict
  the raw count of failing wards (R2 = -0.03; reporting drift dominates).
  Against a trailing baseline: R2 = 0.196, 3-class 50.0% vs 39.6% majority -
  the pre-set bar was missed on R2 and marginal on 3-class. Useful only at the
  extremes: 9 of the 10 most confidently flagged nights were genuinely severe.
  Advisory output, never a headline.
- **The label is real but noisy** (profile §21). 16 of the frozen top-20 wards
  are on BBMP's agency-observed register against a 52% base rate (p = 0.006),
  but severity agreement is only moderate (Spearman 0.334). The label finds real
  places; its error is in timing and degree. Say this in the limitations.
- **PROOF TWO'S NAIVE TEST IS ALL FALSE POSITIVES** (profile §22). Complaint
  volume doubled 2021-2024 and ward growth is not uniform (0.87x-4.81x). Raw
  event counts: **7 wards significantly rising**. Normalised by each ward's own
  complaint volume: **0** - under any of three denominators - while 10 decline.
  **Normalisation is mandatory**, and after it there is no emerging signal at
  ward level at all (closest p = 0.139). Likely a granularity wall: a ward is
  3.7 km2, an emerging hotspot is a junction, and the complaints carry no
  sub-ward geography. Do not report Bellandur, Varthur or Hoodi as emerging.
- **Reporting growth is idiosyncratic, not an equity gradient** (§22.2). SC+ST
  share vs growth rho = -0.057 (p = 0.42); no core/periphery effect. A noise
  problem, not a bias problem.
- **Both proofs are now negative-shaped.** Proof One is a measured ceiling,
  Proof Two a measured confound. The positive contribution has to come from
  intervention effectiveness, which has an independent data source (BBMP ward
  work orders 2013-2022). **This is a project-level decision - see REPORT.md.**

Not started:
- `app/ingestion/bbmp_complaints.py` — the headers are now known and profiled,
  so map explicitly from `docs/02-data-profile.md` §2. Two traps that profile
  documents: filter waterlogging on **`Sub Category`, not `Category`** (84% of
  it sits under `Road Maintenance(Engg)`), and parse the date to **`DATE`,
  not `DATETIME`** (the timestamps lost their AM/PM marker). Keep the
  `--inspect` mode as a header-signature assertion so a republished file with
  a changed vocabulary fails loudly.
- **Decide the waterlogging label before training anything.** `Road side
  drains` is 66% of waterlogging ward-days but is maintenance backlog, not
  flooding — rain lift 1.3x versus 3.1x for `water stagnation`. Profile §12.5
  recommends modelling failure events and maintenance demand as two separate
  targets. This choice partly determines whether Proof One succeeds.
- `app/ingestion/bbmp_hotspots.py` — load the BBMP flood-prone register into
  `locations` with `is_known_hotspot=true` and `first_listed_year` set. The
  register is **KML, not CSV** — three near-disjoint layers, ~390 locations
  rather than the ~210 assumed. `flood_vulnerable_map.kml` is the primary one.
- **`data/reference/ward_crosswalk.csv`** — hand-checked, keyed on `WARDNO`
  1-198. Complaints carry ward *name* only, the register carries ward
  *number*; only 55 of 103 names match exactly. Do not fuzzy-match at load
  time, it mis-pairs real wards. Blocks `geo.py`.
- `app/ingestion/geo.py` — assign each location its nearest `weather_cells`
  row (`Location.cell_id`); haversine is fine at this scale.

### Bringing the stack up

```bash
docker compose up -d
docker exec -i ufms-mysql mysql -uroot -proot < ufms_schema.sql
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
copy .env.example .env                                # then set a real SECRET_KEY
uvicorn app.main:app --reload
```

Green when `/docs` loads and `/api/v1/health` reports `"database": "reachable"`.

Two things that bit on the first run, both fixed — do not reintroduce them:

- **MySQL is on host port 3307, not 3306.** A native Windows MySQL service
  commonly already owns 3306, and the container then fails to bind.
  `docker-compose.yml` maps `${MYSQL_HOST_PORT:-3307}:3306` and `DATABASE_URL`
  in `.env.example` matches. Override `MYSQL_HOST_PORT` if 3307 is taken too.
- **`email-validator` is a real dependency.** `app/schemas/auth.py` uses
  pydantic `EmailStr`, which imports it lazily — so everything installs fine
  and then the app dies on import. It is pinned in `requirements.txt`.

`ufms_schema.sql` opens with `DROP DATABASE IF EXISTS ufms`, so re-running it
wipes all data. The `ufms` user's grants do survive the drop; no re-grant.

Alembic connects but has **no baseline revision** — the schema is loaded from
`ufms_schema.sql`, not migrations, so `alembic revision --autogenerate` would
try to create all 26 tables. Stamp a baseline before writing the first
migration.

## Where the work queue lives

`NEXT.md` at the repo root holds the current task and the queue. Read it, do the
task at the top, move it to the Done log with a one-line result, promote the
next. Do not start queued items early.

Standing evaluation rules and all measured baselines are in
`docs/01-evaluation-rules.md`. **Read that before writing any modelling code** —
in particular, the static baseline to beat is precision@20 = 13.55%, the oracle
ceiling is 37.36%, and count-based memory features are already known to be
saturated.

## What this is

**Urban Failure Memory System.** A **decision support system for preventive
municipal maintenance** — NOT a prediction system, and NOT a "recommendation
system" (that term means collaborative filtering and invites the wrong
questions).

Final-year major project. Team of 2–3. Zero budget. Target: April 2027,
mid-review around 7 December 2026.

### The framing that matters

The city already knows where it floods — BBMP publishes ~210 flood-prone
locations. A system whose output is "these places flood" tells the city what
it compiled by hand years ago. So the question is not *where*, it is:

1. **Triage** — which 20 of the ~210 do we send tonight's crews to?
2. **Emerging** — which locations are becoming the next entry on that list?
3. **Effectiveness** — did last year's desilting actually work?

One-liner for the abstract: *Cities already know where they fail; that
knowledge just isn't operational. UFMS turns scattered institutional memory
into a nightly triage list, surfaces failure points the city hasn't
recognised yet, and measures whether past fixes actually worked.*

## Cities

- **Bengaluru — primary.** Trains, evaluates, supplies every measured number.
  Has complaints (BBMP grievances, 2020–2025, ward level, public domain), a
  hotspot register (BBMP flood-prone areas), and ward work orders
  (2013–2022) for intervention effectiveness. All downloadable.
- **Delhi — demo only.** Same method applied to the PWD hotspot list plus
  Open-Meteo rainfall. **No ground truth, so no evaluation.** Present it as
  an unevaluated portability demonstration. Never report metrics for Delhi.

## Scope — frozen until the mid-review

| Component | Status |
|---|---|
| Waterlogging | Full pipeline |
| Garbage | Operations only (CRUD, dashboard, alerts) |
| Traffic / water shortage / infrastructure | Schema tables only. No modules, no simulated data. |
| Roles | `admin` and `officer` only |
| Cross-city transfer study | Limitations paragraph, not an experiment |

New ideas go in a backlog file, not the build. Scope creep already cost this
project one full revision.

## Non-negotiable engineering rules

1. **No leakage.** Every `failure_memory` row must be computed from data
   strictly earlier than its `as_of_date`. This is the single easiest way to
   invalidate the entire project.
2. **Temporal splits only.** Never `train_test_split(shuffle=True)`. Train on
   earlier seasons, test on later ones. Block by rainfall event so one storm
   cannot appear in both.
3. **Never report accuracy.** Report precision@k, PR-AUC, Brier, and
   calibration error, with the base rate printed beside every figure.
   The measured ward-day base rate is **1.56%** for the strict waterlogging
   label and **7.99%** for the broad one (profile §12), so "no failure" still
   scores 98.4% / 92%. The **~0.5% figure previously quoted here is unsourced**
   — it presumably meant location-days, which cannot be computed until the
   ward crosswalk exists. Derive it then, or stop quoting it.
4. **Persist every ranking.** `daily_rankings` looks recomputable but is not:
   without stored history the ranking-dynamism proof is impossible.
5. **Always write `actual_outcome`.** Closing the loop on
   `risk_predictions` is how the system is ever shown to work.
6. **Labels are complaints, not floods.** Control for each ward's baseline
   complaint rate. Reporting propensity tracks income and civic awareness.
7. **Ingestion filters at source.** Only waterlogging and solid-waste
   categories. Loading all 1.5M BBMP records blows the 1 GB free tier.
8. **Weather is stored per grid cell, not per location.** A few ERA5 cells
   cover a city; per-ward hourly weather would be 10M+ rows.

## The two proofs (first-class deliverables)

**Proof 1 — the ranking is dynamic.** If tonight's top 20 equals every other
night's top 20, this is a report, not a tool. Baseline to beat: a static
"20 historically worst" list. Measure precision@20 plus Kendall's tau
between consecutive events. **Due in Phase 3, before the mid-review**, so
there is time to adapt if it fails.

The baseline is now **measured, not hypothetical** (profile §14, ward level,
strict label, temporal split):

- **precision@20 = 13.6%** for the static list on held-out rain days.
- **Oracle ceiling = 37.4%** — only ~9 wards have an event on a typical rain
  day, so 20 slots cannot all be right. **Always report achieved, baseline and
  ceiling together**; a bare precision@20 reads as failure when it is not.
- Random baseline 4.7%. Re-ranking the static list daily on all prior history
  gives 13.7% — i.e. **memory alone is saturated**, and the headroom to 37.4%
  has to come from weather and location features. That is M3's job.
- **Judge Kendall's tau against 0.59**, the observed static persistence between
  period halves. A model ranking at tau >= 0.59 has reproduced the static list.
- Stratify by rainfall band: the static baseline itself moves from 8.9% on
  2.5-5 mm days to 33.3% on >=25 mm days, a bigger spread than any likely
  modelling gain.
- No reporting lag worth modelling: lag 1 beats lag 0 by 33 events out of
  3,417, p = 0.70 (profile §13). Align rainfall to the complaint date.

**Proof 2 — emerging detection finds real additions.** Mann-Kendall / CUSUM
on complaint rate normalised by rainfall. Validate by training through year
*n* and checking flagged sites show sustained elevation in *n+1*.

## Model ladder (ablation)

- `M0_threshold` — rainfall threshold rule, no ML. The baseline to beat.
- `M1_weather` — weather features only
- `M2_weather_geo` — weather + terrain
- `M3_full_memory` — weather + terrain + Failure Memory Index ← the system

## Stack

FastAPI + SQLAlchemy 2.0 + MySQL 8 + Alembic; React + Tailwind + shadcn +
Recharts + Leaflet (frontend, Phase 4); pandas / scikit-learn for modelling.

Zero budget: local MySQL via `docker compose`, **Aiven** free tier for hosted
MySQL (Railway killed its free tier), Render for the API, Vercel for the
frontend, Open-Meteo for weather (free, no key). Train from Parquet, not
MySQL — the database is the system of record, the panel is a derived artifact.

## Layout

```
app/
  core/          config, security (JWT + bcrypt), exceptions, logging
  db/            engine, session, declarative base
  models/        26 SQLAlchemy models mirroring ufms_schema.sql
  schemas/       Pydantic request/response models
  repositories/  data access; keeps SQLAlchemy out of services
  services/      business logic; owns transactions (commit here, not in routes)
  api/v1/        routers
  middleware/    request logging with correlation ids
```

See `docs/` for the build plan and the evaluation rules — read `docs/01-evaluation-rules.md` before writing any modelling code.

`ufms_schema.sql` at the repo root is the canonical DDL. The SQLAlchemy
models mirror it — change both together, or generate a migration.

## Conventions

- Services commit; routes and repositories never do.
- Raise `UFMSError` subclasses (`NotFoundError`, `ConflictError`, `AuthError`,
  `PermissionError_`) — handlers turn them into consistent JSON.
- Login failures return one message for both wrong-email and wrong-password.
- Officers do not self-register; `/auth/register` is admin-only.

## Deferred decisions (do not silently "fix" these)

- **Alembic baseline — deferred to Phase 2.** `versions/` is intentionally
  empty; the schema comes from `ufms_schema.sql`. Do NOT run
  `alembic revision --autogenerate` before baselining, or it will emit a
  migration that recreates all 26 tables. When it is done properly: generate
  the baseline against an EMPTY database so migrations can build the schema
  from scratch (Render needs this in Phase 7), hand-add the 3 views with
  `op.execute`, verify a fresh `alembic upgrade head` produces an
  `information_schema` identical to loading the raw SQL, then
  `alembic stamp head` on the existing dev database.

- **`ufms_schema.sql` is no longer destructive.** The `DROP DATABASE` moved
  to `scripts/reset_db.sql`. Re-running the schema file on a populated
  database now fails loudly instead of wiping Phase 1 data. Do not
  reintroduce `DROP DATABASE` into the schema file.

- **`/health` returns 503 when the database is unreachable**, not 200.
  Platform health checks read the status code, not the body. Keep it that way.
