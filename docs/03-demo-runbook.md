# Demo runbook

**Execute this literally. Do not improvise on the day.**

Assumes a machine with this repository cloned and nothing else running. Every
command is run from the repository root unless it says otherwise.

The rehearsal on **15 September** is defined as: follow this file exactly, on
the machine that will be used on the 16th, changing nothing, and note every
place it fails.

> **The demo runs from localhost.** If a deployed URL exists it is a line on a
> slide, not the demonstration — free tiers sleep and college networks are
> hostile. See `04-deploy.md`.

---

## 0. Once per machine

```bash
python -m venv .venv
.venv\Scripts\activate                    # Windows;  source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                    # then set a real SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"

cd frontend && npm install && cd ..
```

Leave `ENVIRONMENT=development` in `.env`. The production guard in
`app/core/config.py` will refuse to start on a placeholder secret, which is
correct for a deployment and a nuisance on a demo laptop.

---

## 1. Cold start — five steps, three terminals

### Step 1 — database (terminal 1)

```bash
docker compose up -d
docker compose ps                          # STATUS must say (healthy)
```

**Read the `docker compose ps` output; do not trust the exit code.**
`docker compose up -d` **exits 0 even when it failed to start the container**, so
an error scrolling past is easy to miss. If `docker compose ps` prints only a
header row and no container, it did not start — go to the failure table below.

**MySQL is on host port 3307, not 3306.** A native Windows MySQL service
usually already owns 3306.

Wait for `(healthy)` before step 2. It takes 20–40 seconds from cold. Starting
the API against a container that is still initialising gives a confusing
connection error rather than a clear one.

### Step 2 — schema

```bash
alembic upgrade head
```

Builds all 32 tables and the 3 views from nothing, plus Alembic's own
`alembic_version`. Idempotent — safe to re-run, and on an already-migrated
database it prints nothing and exits 0.

### Step 3 — data

If this machine has the full database already loaded, skip to step 4.

Otherwise restore the derived rows the dashboard reads — 4,820 rows, 612 KB:

```bash
docker exec -i ufms-mysql mysql --default-character-set=utf8mb4 \
    -uroot -proot ufms < data/processed/demo_data.sql
```

**The charset flag is not optional.** Without it, two column comments are stored
double-encoded.

This does **not** include user accounts. Create them:

```bash
python scripts/create_user.py --email demo.officer@ufms-demo.org \
    --name "Demo Officer" --role officer --password ufms-demo-2026
python scripts/create_user.py --email demo.admin@ufms-demo.org \
    --name "Demo Admin" --role admin --password ufms-demo-2026
```

The shared password is fine here and **only** here: this is a local machine that
is not reachable from anywhere. Anything with a public URL gets generated
passwords instead — `04-deploy.md`.

> Rebuilding the derived tables from raw data instead — `python -m
> app.ingestion.cli derive` — needs `data/raw/`, which is not in the repository
> because it is large and re-fetchable. On demo day, restore the dump. Do not
> try to re-derive.

### Step 4 — API (terminal 2)

**Activate the venv again.** This is a new terminal and it does not inherit the
activation from step 0 — without it, `uvicorn` is "command not found":

```bash
.venv\Scripts\activate                     # Windows;  source .venv/bin/activate
uvicorn app.main:app --reload              # :8000
```

Green when `http://127.0.0.1:8000/api/v1/health` reports
`"database": "reachable"`.

### Step 5 — frontend (terminal 3)

```bash
cd frontend
npm run dev                                # :5173, proxies /api to :8000
```

Open **http://localhost:5173** and sign in as `demo.officer@ufms-demo.org`.

### Step 6 — prove it is serving the right numbers (terminal 1)

```bash
python scripts/check_parity.py --base http://127.0.0.1:8000
```

Must print `27/27 checks passed` and `PASSED`. This takes five seconds and
catches the failure that matters: a stack that boots, renders, and is serving a
database whose derived tables are empty or stale. **Run this before the
examiner is in the room, on the morning of the 16th.**

Optionally, `pytest -q` and, in `frontend/`, `npm test`. Expect:

| Where | Expect |
|---|---|
| A machine with `data/raw/` (the full dev setup) | **148 passed** |
| A fresh clone (no `data/raw/`) | **135 passed, 13 skipped** |
| Frontend, anywhere | **31 passed** |

The 13 skips name themselves — they need the gitignored raw CSVs and KML. A skip
count above 13 means something else is wrong; in particular, if
`tests/test_migrations.py` skips with *"cannot create the throwaway test
databases"*, the database was created before `scripts/mysql-init/` existed. Only
a fresh volume runs that init script, so recreate it with
`docker compose down -v && docker compose up -d` and redo steps 2-3.

---

## 2. When it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `docker compose up` → `port is already allocated` | something owns 3307 | `set MYSQL_HOST_PORT=3310` (and the same port in `DATABASE_URL` in `.env`), then `docker compose up -d` |
| `docker compose up` → `the container name "/ufms-mysql" is already in use` — **and it still exits 0** | another checkout of this project, or a stale container from an older one, already owns that name | If it is stale: `docker rm -f ufms-mysql`. If it belongs to a copy you want to keep: `set MYSQL_CONTAINER_NAME=ufms-mysql-demo` **and** `set MYSQL_HOST_PORT=3310`, put that port in `DATABASE_URL`, then use the new name in every `docker exec` command below. |
| `uvicorn` or `npm run dev` → `address already in use` / `only one usage of each socket address` | something already holds 8000 or 5173 — often a uvicorn or vite from an earlier attempt that did not shut down cleanly | `uvicorn app.main:app --reload --port 8001`, and for the frontend `npm run dev -- --port 5174`. **If you move the API off 8000, the Vite proxy no longer finds it** — change the target in `frontend/vite.config.ts` too. On Windows a dead socket can linger for a minute with no owning process; waiting clears it. |
| Worse version of the above: **8000 answers, but every panel is empty and `/health` says `unreachable`** | An orphaned `uvicorn --reload` **worker** from an earlier run still holds the port and is serving a database that no longer exists. `netstat` blames a PID that no longer exists, so `taskkill` on it reports "process not found" while the port keeps answering. | The live process is the reload worker, not the parent. Find it by command line, not by port: in PowerShell, `Get-CimInstance Win32_Process -Filter "Name='python.exe'"` and look for one with `spawn_main(parent_pid=...)`, then `Stop-Process -Id <that pid> -Force`. Start the API again and run step 6. |
| API: `Can't connect to MySQL server` | container not healthy yet, or Docker Desktop is not running | `docker compose ps`; if there is no container at all, start Docker Desktop and wait for the whale icon to settle |
| `/api/v1/health` returns **503** | API is up, database is not | This is deliberate — the status code, not the body, is the truth. Go back to step 1. |
| Screens render but every panel is empty | signed in, but the derived tables have no rows | run step 6; if it fails, re-run step 3 |
| Login fails with **422** | the email's domain is a reserved TLD (`.test`, `.local`) | use a real-looking domain — `email-validator` rejects the others |
| **Token expires mid-demo** (60 minutes) | expected behaviour | Sign in again. It takes five seconds, and a refresh no longer loses the session — the token is in `sessionStorage`, so **F5 is safe**. Closing the tab does sign you out, which is intentional. |
| A screen shows a blank where a number should be | an unscored snapshot | correct behaviour — nothing substitutes a plausible number for an absent one. Say so; it is a design decision, not a bug. |
| Map renders with no ward shading | `frontend/public/bbmp-wards.geojson` is missing or truncated | It is **committed** (661 KB, 198 wards), so restore it: `git checkout -- frontend/public/bbmp-wards.geojson`. Do **not** run `scripts/export_ward_geojson.py` here — it reads `data/raw/bbmp_ward_map_2015.kml`, which is gitignored, so on a clone it fails with a `FileNotFoundError`. Regenerating is only possible where the raw data is. |
| `npm run visual-check` / `npm run figures` fails instantly | Playwright's browser is not installed | `npx playwright install chromium` — a missing browser, not a broken check |

**Insurance, in order of preference.**

1. **`docs/demo/ufms-demo.mp4`** — 1:12 at 1280×720, a recording of this exact
   system walking this exact path. It covers every failure that is not the
   software: a flat battery, no HDMI adapter, a projector that will not sync,
   being asked to present from the podium machine, Docker refusing to start.
   **Copy it onto the same USB stick as the slides.** Run the live demo whenever
   it is possible; reach for this when it is not.
2. `docs/figures/screen-*.png` — the four screens as stills, already rendered
   from the live system. If even video will not play, the figures carry the
   argument.

---

## 3. The five-minute path

Four screens, in this order. **Do not reorder — screen 2 is second for a
reason.** It carries the whole argument, and if the demo runs short it is the
one that must already have been shown.

### 1. Watchlist — the result (90 seconds)

*The landing screen. Start here.*

> "This is tonight's triage list — the twenty wards a crew would be sent to.
> The number under it is precision@20: of the twenty we named, 14.08% had a real
> waterlogging event on a held-out rain night."

Then, immediately, the point of the screen:

> "That number is meaningless alone, which is why it is drawn as a mark on a
> scale rather than as a statistic. Picking twenty wards at random scores 4.79%.
> A perfect oracle — one that knows the answers — scores 37.72%, because a
> median rain night only has about six flooded wards citywide and twenty slots
> cannot all be right. So we are at 37% of everything achievable, and about
> three times chance."

**Never say the 14.08% without the 4.79% and the 37.72%.** Under questioning
this is exactly what gets said loosely. The figure was built so that it cannot
be drawn without its scale; say it the same way.

### 2. Ward index — what the system is reading (60 seconds)

> "This is one ward's relative flooding index over twenty quarters. The line at
> 1.00 is the city norm — complaint volume roughly doubled between 2021 and
> 2024, so a raw count of complaints shows reporting growth and reads as
> flooding. Everything here is benchmarked against the city's own trend."

Show the map:

> "All 198 wards for one quarter. It diverges about 1.00 — blue below the norm,
> red above — because 1.00 is a real midpoint, not a colour choice. There is no
> road map underneath deliberately: the wards tile the city, so they *are* the
> map, and a basemap under a diverging colour scale competes with the encoding."

Hover a ward to show the name, index and quarter.

### 3. Emerging — the honest one (60 seconds)

> "These are wards becoming a problem that are not on BBMP's official register.
> The label is *chronically above norm* — not *accelerating*. Ten flagged wards
> finish the second half at a mean index of 1.77 against 1.16 for all wards, and
> ten out of ten are above the norm, p = 0.0001. But they do not significantly
> exceed their own first half, p = 0.116, so the detector finds places that are
> persistently bad, not places that are getting worse."

Point at the banner:

> "And this says `ground_truth_available: false`. BBMP's register carries no
> listing years, so we cannot check a single one of these flags against the
> city's own later additions. We show that rather than hide it."

### 4. Allocation — the finding (90 seconds)

> "Two scatter plots, and the difference between them is the finding. On the
> left, drainage spend against ward area: ρ = +0.474. On the right, the same
> spend against relative flooding need: ρ = +0.082, p = 0.39 — nothing.
> **BBMP allocates drainage spend by ward size, not by need.**"

Then the retraction, out loud, before anyone asks:

> "We originally reported that spending reduced flooding. It did not survive
> refitting on treated wards only — it went from p = 0.014 to p = 0.83, because
> seven untreated wards were doing the work. We retracted it, and the retraction
> is rendered on the screen rather than dropped from the slides."

**There is no trend line on either panel and there must never be one.** A line
through a scatter is read as an effect estimate whatever the caption says, and
the effect estimate is precisely what was retracted.

---

## 4. What is not built — say it before you are asked

Being asked "what's missing?" and having a crisp list is a much better position
than being caught by one item on it.

- **No alerting loop.** No notifications, no scheduled nightly job. The
  watchlist is a stored snapshot served by an endpoint.
- **No outcome recording.** `risk_predictions.actual_outcome` is never written,
  so the loop that would prove the system works over time is designed and not
  running.
- **`interventions` is intentionally empty.** The work orders are aggregated
  into `ward_allocation`; no screen needs row-level work orders, so loading
  49,915 rows with no consumer would be busywork. This is a decision, not an
  omission.
- **`ground_truth_available: false` on the emerging screen**, because BBMP's
  register carries no listing years. The flags cannot be validated against the
  city's own additions, and the screen says so.
- **No model.** The within-ward design failed at the gate: zero wards have their
  first drainage work inside the study window, so no observational design is
  identifiable on these records. The measured ceiling is the deliverable.
- **Two roles, read-only.** `admin` and `officer` both read everything; there is
  no mutation UI.
- **Delhi is not evaluated.** No ground truth, so no metrics — a portability
  demonstration only.

---

## 5. Shutting down

```bash
docker compose down          # add -v only if you intend to lose the data
```

`Ctrl+C` in terminals 2 and 3.
