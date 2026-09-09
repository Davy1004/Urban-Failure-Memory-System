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
- **PROOF TWO: normalise, and NEVER test against zero** (profile §22-§23).
  Raw event counts give 7 rising wards - all reporting-growth artefacts, so
  normalisation by each ward's own complaint volume is mandatory. But testing
  the normalised slope against **zero** is also wrong, because the citywide
  share fell 22%: that gave a false 0-rising. Benchmarked to the **city trend**
  (`events / (complaints x city_share)`) the answer is **9 rising, 4 declining**,
  permutation p = 0.0010. **FDR leaves exactly one nameable ward: Jakkur**
  (pre-specified non-register pool, q <= 0.10); split-half slope correlation is
  0.035. Real in aggregate, barely identifiable per ward. Do not report
  Bellandur, Varthur or Hoodi as emerging - Hoodi is significantly declining.
  **Never call a share decline "improvement" without checking absolute counts**;
  4 of 10 zero-null decliners had absolute events rise.
- **Reporting growth is idiosyncratic, not an equity gradient** (§22.2). SC+ST
  share vs growth rho = -0.057 (p = 0.42); no core/periphery effect. A noise
  problem, not a bias problem.
- **Work orders are feasible and are the strongest output on data** (§24).
  ~1,350 usable drainage works across 166 wards, 2021-01..2022-12; ward, date
  and cost complete for 183 of 198 wards; drainage separable at 36% of rows.
  **Wards 184-198 use a legacy schema with no dates - unusable.** Only 32 wards
  are untreated, so use **dose-response on spend** (median Rs 19.5M, max
  Rs 632M), not treated-vs-control. Jakkur - the one FDR-surviving emerging
  ward - is the 2nd-highest drainage spender at Rs 494M, which is a ready-made
  case study.
- **INTERVENTION EFFECTIVENESS: OUTCOME CLAIM RETRACTED** (profile §27.2).
  **There is no dose-response.** The published -0.0240 (p = 0.0138) vanishes
  when refitted on treated wards only: **-0.0064, p = 0.833**. `log1p(spend)`
  put 7 untreated wards at 0 against treated wards at 16-20, so it was a
  treated-vs-control contrast - and those 7 are not a valid control. **Rule:
  refit any dose-response on treated units only before reporting it**, and use
  an added-variable plot, which is what caught this. What survives is the
  ALLOCATION finding, which is untouched and independent of any outcome model:
  the
  reverse-causality confound is **measurably absent** - spend vs pre-period
  index r = -0.083 (p = 0.39); spend tracks **ward area** (rho +0.474), not
  flooding need - **BBMP allocates drainage spend by ward size, not need.**
  **The targeting objection is answered** (§26.5): spend vs
  absolute events is +0.274 raw but **-0.050 (p = 0.60) controlling for area**.
  **The apparent non-monotonicity is NOT real** (§26.3) - only the lowest-spend
  quintile differs from zero, and a quadratic term is not significant
  (F = 1.26, p = 0.265). Publish the quintile table with CIs. Do not claim
  causality: spend is discretionary, not randomised, and the effect is
  significant only conditional on controls (raw Spearman -0.163, p = 0.099).
- **Jakkur: the spend came first.** Rs 346M in 2020 and Rs 494M in 2021-22,
  while the relative index went 0.55 (pre) -> 0.93 (during) -> 1.42 (post). The
  "works were a response to deterioration" reading is not supported. Caveat: the
  work-orders data ends in 2022, so post-2022 blank spend is censoring.
- **RETRACTED:** §24's claim that register-absent wards get more drainage spend.
  Across all 198 wards, p = 0.789. It was a four-ward coincidence.
- **Emerging detection: test LEVEL persistence, not slope.** Slope correlation
  across halves (0.035) is low by construction. Top-10 slope-flagged wards end
  at mean relative index 1.77 vs 1.16 for all wards, **10/10 above the city
  norm, p = 0.0001**. The detector finds *chronically above norm*, not
  *accelerating*.
- **THE WITHIN-WARD DESIGN IS DEAD AT THE GATE** (profile §28). Staggered
  treatment timing does not exist: **zero** wards have their first-ever
  drainage work inside 2021Q1-2022Q4 (all 196 were first treated 2011-2014),
  the median ward had works completing in **6 of the 8 quarters before** the
  window, only **4 of 8** quarters carry >= 5 first-treated wards, ward work
  profiles correlate with the citywide calendar at rho = +0.505, and the
  work-order file stops at 2023Q1 while the outcome panel runs to 2025Q1 - so
  40% of the "post" period is censoring. **No model was fitted; the gate is
  the result.** Also: 5 of the 7 "untreated" wards had ₹37-121 M of drainage
  work before the window, so the treated indicator (-0.4497) is not a
  treated-vs-control contrast either and must not be reported as a fallback.
  **ANALYSIS IS CLOSED PERMANENTLY.** Do not propose another identification
  strategy on this data.
- **The effectiveness output is the ALLOCATION finding, in full.** Spend tracks
  ward area (rho = +0.474), not relative flooding need (r = -0.083, p = 0.39).
  Its companion, and use this wording rather than any claim about what BBMP
  knows: drainage works are distributed continuously and near-uniformly across
  all 198 wards and have been since 2013, so **no observational evaluation of
  their effect is identifiable from these records** - the treatment does not
  vary enough for any design to exploit.
- **Proof One is a measured ceiling; Proof Two is real but barely nameable;
  intervention effectiveness is positive.** **The analysis should now stop
  expanding and the queue should turn to building** - the system has not moved
  since Phase 0 and the mid-review is ~7 December.

- **PHASE 4 IS DONE: the frontend exists** (9 Sep 2026). `frontend/` **inside
  this repository** (it was a sibling directory until 9 Sep and is not any
  more — see below), React 19 + Vite + Tailwind v4 + Recharts + Leaflet, four
  screens on the five endpoints. `npm run dev` proxies `/api` to :8000. **Read
  `frontend/README.md` before changing a screen** — several presentation
  rules there are results, not taste. In particular precision@20 is drawn as a
  mark on a scale ending at the oracle ceiling, never as a stat tile: the
  context is structural, so it cannot be dropped without breaking the drawing.
  25 frontend tests pin those rules in the rendered DOM.
  Two things a reader should know: **the ward polygons are generated** by
  `scripts/export_ward_geojson.py` from `bbmp_ward_map_2015.kml` (the 2022 KML
  is a different delimitation and will not join), and **the map has no
  basemap** — the 198 wards tile the city, and the CARTO tiles started
  demanding an API key.
- **A fifth endpoint exists: `GET /api/v1/index`** (no ward), returning every
  ward's index for one quarter. The choropleth needs all 198 at once; built
  from 198 per-ward calls it renders half-shaded when one fails, and an
  uncoloured ward reads as "nothing happened here" rather than "no data".
- **The four derived tables and their endpoints are built** (9 Sep 2026).
  `ward_quarter_index` (3,960 ward-quarters), `watchlist_snapshots` +
  `watchlist_entries`, `emerging_watch` (103 eligible wards) and
  `ward_allocation` (110 wards, 103 treated), rebuilt by
  `python -m app.ingestion.cli derive`. Endpoints `/api/v1/index/{ward}`,
  `/watchlist`, `/emerging`, `/allocation`, all GET, both roles.
  **Every one reconciles exactly against the reference CSVs** —
  `tests/test_derived.py`, 32 assertions at 1e-9, plus 31 response-contract
  tests in `tests/test_dashboard_api.py`. Two things worth knowing:
  **the random baseline on the IFS basis is 4.79%, not 4.72%** (4.72% belongs
  to the ERA5/138-day basis, where the static list is 13.55% and the ceiling
  37.36%. `docs/01-evaluation-rules.md` now leads with the IFS triple
  **4.79 / 14.08 / 37.72** and keeps the ERA5 one beneath it, labelled), and
  **`locations.is_known_hotspot` is FALSE for all 198 ward rows** because the
  flag is set on the 398 register points — the ward-level register fact lives
  in `ward_crosswalk.csv`'s `in_flood_register`, and reading it from
  `locations` would silently widen the pre-specified emerging pool from 42
  wards to all 103.
- **Migrations are live.** `alembic upgrade head` builds the whole schema from
  scratch, views included; `weather_cells.model` records which reanalysis each
  cell is (era5 = cells 1-9, ecmwf_ifs = 10-23, backfilled, and `model` is part
  of `uq_cell_coords` because two models may snap to one coordinate); and
  `ward_period_totals` holds the index denominator in the database, so the
  relative flooding index no longer needs a CSV beside it. 4,356 ward-quarter
  rows, matching `ward_period_totals.csv` exactly and idempotently.

Not started:
- **`is_known_hotspot` is set but `first_listed_year` is NULL for all 398
  register points.** The KML layers carry no year, so the "which locations did
  the city add this year" framing has no ground truth on the register side.
  Decide whether to drop the field or source the years elsewhere.
- **Hotspot register dedup.** The three KML layers are loaded unmerged, so the
  398 points contain an unknown number of duplicates across layers. Queue item.
- Memory engine and the model ladder M0-M3 — to demonstrate the bound, not to
  beat it. Report within-night AUC or precision@k, never a pooled AUC.

Done since this list was last accurate — do not re-plan these:
`app/ingestion/bbmp_complaints.py` (YAML-driven, 237,157 complaints, matched on
`Sub Category` and truncated to `DATE` as the profile requires); the
waterlogging label decision (`data/reference/hazard_categories.yaml`, event vs
maintenance split); the flood register (loaded by `app/ingestion/bbmp_wards.py`,
398 points, not a separate `bbmp_hotspots.py`); `ward_crosswalk.csv` (198 rows,
0 unresolved); and cell assignment (also in `bbmp_wards.py`, all 596 locations
carry a `cell_id` — there is no `geo.py` and none is needed).

### Bringing the stack up

```bash
docker compose up -d
alembic upgrade head                       # builds the schema from migrations
# or load the canonical DDL directly. The charset flag is not optional:
# without it, two column comments are stored double-encoded.
# docker exec -i ufms-mysql mysql --default-character-set=utf8mb4 \
#   -uroot -proot < ufms_schema.sql
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

**The models did NOT mirror `ufms_schema.sql`, and nothing had noticed.**
Baselining exposed **178 differences**: all 45 foreign keys and 27 indexes
carried MySQL's auto-generated names (`weather_cells_ibfk_1`) rather than the
schema's (`fk_cell_city`), 23 columns had a Python-side `default=` and so no
server-side DEFAULT at all, seven `TIMESTAMP` columns had become `DATETIME`,
`cities.country` was `VARCHAR(2)` not `CHAR(2)`, `users.updated_at` had lost
`ON UPDATE CURRENT_TIMESTAMP`, and all 25 column comments were missing. The
Phase 0 note that "table sets match exactly, no column drift" was true and
insufficient — it compared names, not types, defaults or constraint names. The
models are now faithful and the test above keeps them that way.

**Load the schema with an explicit charset.** `docker exec -i ufms-mysql mysql
-uroot -proot < ufms_schema.sql` negotiates a latin1 client charset and
double-encodes the two column comments containing an em-dash. Always pass
`--default-character-set=utf8mb4`.

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
  models/        31 SQLAlchemy models mirroring ufms_schema.sql
  derived/       the four dashboard computations; reconciled, not ingested
  schemas/       Pydantic request/response models
  repositories/  data access; keeps SQLAlchemy out of services
  services/      business logic; owns transactions (commit here, not in routes)
  api/v1/        routers
  middleware/    request logging with correlation ids
```

See `docs/` for the build plan and the evaluation rules — read `docs/01-evaluation-rules.md` before writing any modelling code.

The frontend lives in `frontend/`, a separate npm project **inside this
repository**. It was a sibling directory (`../ufms-frontend`) until 9 Sep 2026,
which meant it was in no version control at all; it is now tracked here, and
`/frontend/node_modules/` and `/frontend/dist/` are ignored at the repo root.
`scripts/export_ward_geojson.py` writes to `frontend/public/`, a path inside the
repository, and `frontend/scripts/paper-figures.mjs` writes to `docs/figures/`.
Do not restructure this into `backend/` + `frontend/` under a new root — every
path in every doc is written against this layout. It talks to this API only — it holds no analysis of its own, and every caveat it renders
arrives as a required response field so a redesign cannot silently drop one.

`ufms_schema.sql` at the repo root is the canonical DDL. The SQLAlchemy
models mirror it — change both together, or generate a migration.
Section 7 holds the five derived tables; `app/derived/` computes them and
`tests/test_derived.py` reconciles every one against a committed reference CSV.
**A column COMMENT is a SQL string literal, and one containing a semicolon cut
`test_migrations.py`'s statement splitter in half.** The splitter is now
quote-aware, so prose comments are safe.

## Conventions

- Services commit; routes and repositories never do.
- Raise `UFMSError` subclasses (`NotFoundError`, `ConflictError`, `AuthError`,
  `PermissionError_`) — handlers turn them into consistent JSON.
- Login failures return one message for both wrong-email and wrong-password.
- Officers do not self-register; `/auth/register` is admin-only.

## Deferred decisions (do not silently "fix" these)

- **Alembic baseline — DONE (8 Sep 2026), no longer deferred.** Three
  revisions: `d592327e5d7c` baseline (26 tables + the 3 views by `op.execute`),
  `bcaacf1141de` `weather_cells.model`, `5fabc9db9f7d` `ward_period_totals`.
  The dev database is stamped and `alembic check` is clean against it.
  `alembic upgrade head` on an empty database now produces an
  `information_schema` identical to loading `ufms_schema.sql` — enforced by
  `tests/test_migrations.py`, which builds one database each way and diffs
  columns, types, defaults, ordinal positions, comments, indexes, foreign keys
  and view definitions. **Run that test after touching either file.**

- **`interventions` is intentionally empty and must stay that way.** The work
  orders are aggregated into `ward_allocation` by `app/derived/allocation.py`
  and the 49,915-row extract stays on disk, exactly as `ward_period_totals`
  does with the complaint totals. No screen needs row-level work orders, so
  loading them would be 49,915 rows with no consumer. Do not helpfully
  populate it.

- **`ufms_schema.sql` is no longer destructive.** The `DROP DATABASE` moved
  to `scripts/reset_db.sql`. Re-running the schema file on a populated
  database now fails loudly instead of wiping Phase 1 data. Do not
  reintroduce `DROP DATABASE` into the schema file.

- **`/health` returns 503 when the database is unreachable**, not 200.
  Platform health checks read the status code, not the body. Keep it that way.
