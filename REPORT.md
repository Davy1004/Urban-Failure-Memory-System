# REPORT — 10 September 2026

Task: the three items under "Current task" in `NEXT.md` — frontend into version
control, a time-boxed deploy attempt, and the demo runbook. Plus the five §9
answers, which were instructions rather than questions this time.

**Items 1 and 3 are complete. Item 2 is complete up to the point where it needs
somebody to create an account, and everything before that point is verified
end to end rather than merely written down.**

Three commits, all pushed to `origin/main`:

| | |
|---|---|
| `f127ccd` | the Phase 1–3 backend backlog that had never been pushed |
| `1eb64c4` | the frontend moved into the repository, plus the §9 changes |
| `33a7ba1` | the runbook, the deploy preparation, and the production guard |

`git status` is clean, `git log origin/main..HEAD` is empty, `.env` is untracked
and ignored. **148 backend tests and 31 frontend tests pass** (up from 143 and
25).

---

## 1. The version-control problem was larger than you described

You were right that this was worse than "slightly awkward for a deploy". It was
also worse than the frontend.

`ufms-frontend/` was untracked, as you said. But **`origin/main` was still on
`1730b71`, "Phase 0: schema, models, JWT auth, API scaffold"** — the commit from
7 September. Ahead of it, locally and nowhere else, were:

- **13 unpushed commits** covering the entire ingestion pipeline, the ward
  crosswalk, the IFS switch, and every analysis result from §13 to §28;
- **a 48-file uncommitted working tree** holding the Alembic bundle, the four
  derived tables, `app/derived/`, the five endpoints, the three test files, and
  the nine figures.

So the exposure was not four screens and 25 tests. It was Phases 1 through 4 —
every measured number in the paper — on one disk. The frontend was the visible
half of the problem.

I pushed the backend backlog first, before touching the move, on the grounds
that the point of the exercise is to stop the work existing in one place and
that ordering minimised the window. It went out as one commit rather than two;
splitting the migration work from the derived-tables work would have required
reconstructing which model edits belonged to which, with a real risk of a
non-building intermediate commit, and the backup mattered more than the history.
**Flagging that as a judgement call** in case you would rather it had been split.

Verification, deliberately not by trusting the ignore pattern:

- 45 files staged in the move commit; `git diff --cached --name-only | grep -cE
  'node_modules|/dist/'` returned **0**.
- `git check-ignore -v frontend/node_modules/react/package.json` names
  `.gitignore:37:/frontend/node_modules/`. Patterns are anchored with a leading
  slash so they cannot match a Python directory of the same name.
- The frontend's own `.gitignore` was deleted, not left to shadow the root one.
- `.gitattributes` already covers the new file types sensibly (`* text=auto
  eol=lf`, `*.png binary`).

### Paths that crossed the boundary

| Was | Now |
|---|---|
| `export_ward_geojson.py` → `ROOT.parent / "ufms-frontend" / "public"` | `ROOT / "frontend" / "public"` |
| `paper-figures.mjs` → `../ufms-backend/docs/figures` | `../docs/figures` |

The geojson exporter is checked rather than assumed: re-running it from the new
path **reproduced the committed 661 KB file byte-for-byte** (198 wards, 36,369
points; `git status` reported no change afterwards).

The dev proxy needed no change — it already targets `127.0.0.1:8000` and is
origin-relative.

Also fixed, all of which assumed the old layout or were simply wrong:

- `frontend/README.md` — paths, plus a `cd frontend` that was missing from the
  run sequence.
- `docs/figures/README.md` — the regenerate block had two `cd`s that only worked
  if you guessed they were separate terminals. Rewritten as three terminals with
  paths from the repository root.
- `README.md` — the schema-load command was wrong twice: it pointed at
  `../ufms_schema.sql`, and it omitted `--default-character-set=utf8mb4`, which
  CLAUDE.md calls non-optional because without it two column comments store
  double-encoded. Its endpoint table was also missing all five dashboard
  endpoints.
- `CLAUDE.md` — three layout references, plus a note recording that the sibling
  layout is gone and must not be reintroduced as `backend/` + `frontend/`.

---

## 2. Deploy: the design note is right, and I proved it locally

### Where it stopped, and why

**No deploy CLI exists on this machine** — no `gh`, `vercel`, `render`,
`flyctl`, `railway` or `aiven`, and no `mysql` client either. Provisioning any
of the three services means creating accounts through a browser and accepting
terms, which is not something I can or should do on Tanmay's behalf.

So I took the attempt as far as it goes without an account, and made the
remaining part a short, ordered click path rather than a discovery exercise.

### Providers, checked this week rather than trusted

| Service | Free? | Card? | The catch |
|---|---|---|---|
| **Aiven MySQL** | yes, always-free, 1 GB storage / 1 GB RAM, single node | **no** | **powers off after a period of inactivity** |
| **Render web service** | yes, 750 instance-hours/month | **no** | **spins down after 15 min idle, ~1 min to wake** |
| Vercel static | yes | no | none that matters |

So the deploy is possible on free tiers with no card — and **both moving parts
sleep**. Your condition one was not a precaution, it is the expected case: a
cold demo would be a one-minute Render wake on top of an Aiven instance that may
be powered off entirely. The runbook therefore says localhost, and `04-deploy.md`
opens by saying the URL is a slide, not the demonstration.

I did **not** port anything to Postgres.

### The design note, verified

Your note was that the deployed database does not need the full dataset. It is
correct, and by more than the argument implied. Measured:

| | rows | size |
|---|---:|---:|
| `weather_observations` | 1,309,896 | 146.3 MB |
| `complaints` | 237,157 | 64.1 MB |
| `weather_daily` | 54,881 | 5.0 MB |
| **everything the five endpoints read** | **4,820** | **612 KB dumped** |

The closure is exactly nine tables — `cities`, `failure_types`,
`weather_cells`, `locations`, `watchlist_snapshots`, `ward_quarter_index`,
`watchlist_entries`, `emerging_watch`, `ward_allocation` — and it **closes**: I
pulled every FK on those tables out of `information_schema` and nothing points
outside the set except `users.city_id`. `scripts/export_demo_dump.py` re-runs
that check on every invocation, so adding a repository that reads a new table
fails the dump with the missing table's name instead of producing a file that
breaks on somebody else's machine.

### Then I actually ran the whole thing

Not a plan — executed, against a second MySQL 8.0 container on port 3308
standing in for the hosted database:

1. Empty MySQL. `alembic upgrade head` → 32 tables and 3 views from nothing.
2. Restore the 612 KB dump → 4,820 rows, all counts matching, `users` = 0 as
   designed. Ran it twice; the second run is a clean no-op (every statement is
   `INSERT … ON DUPLICATE KEY UPDATE`).
3. `scripts/create_user.py` → one account, generated password.
4. Fresh venv, `pip install -r requirements-api.txt` only → 335 MB.
5. Boot with `ENVIRONMENT=production DEBUG=false` and a real secret.
6. `scripts/check_parity.py --base <local> --other <restored>`.

Result:

```
Frozen invariants, 27 of them
  http://127.0.0.1:8000: 27/27 checks passed
  http://127.0.0.1:8002: 27/27 checks passed

Field-by-field diff, relative tolerance 1e-09
  /api/v1/watchlist            identical
  /api/v1/index                identical
  /api/v1/index/Jakkur         identical
  /api/v1/emerging             identical
  /api/v1/allocation           identical

PASSED - both instances agree, and on the published numbers
```

**A database holding only the derived tables serves byte-identical JSON to the
full 215 MB one.** The risky unknown in your task 2 is now a measured fact.

The 27 invariants are the published figures, not tuned thresholds:
precision@20 = 0.14080882 with `random_at_k` 0.04786839 and `oracle_at_k`
0.37720588; 136 test rain days and 1,289 events; `weather_model = ecmwf_ifs`;
ρ = +0.4740946 for spend-vs-area against +0.0824532 (p = 0.3918) for
spend-vs-need; −0.0500933 controlling for area; 103 eligible and 10 flagged
wards with `flagged_above_norm = 10`, p = 0.000144 and p = 0.116; Jakkur's mean
1.0947569 over 20 quarters; 198 wards in the city index; the frozen top-20 head
`Bellandur, Horamavu, Thanisandra, Begur, Ramamurthy Nagar` in rank order; and
non-empty `retraction` and `caveats`.

It runs against one URL too, which makes it the pre-demo smoke check —
five seconds, and it catches the failure that actually happens: a stack that
boots and renders against derived tables that are empty or stale.

### CORS

Tested, not assumed. With `CORS_ORIGINS=["https://ufms-demo.vercel.app"]`, a
preflight from that origin returns `access-control-allow-origin` for it, and a
preflight from another origin returns 400 with no allow-origin header.

`frontend/vercel.json` uses a **rewrite** rather than a cross-origin call, so the
browser only ever talks to the Vercel origin and there is no CORS to get wrong —
the same arrangement the Vite dev proxy gives locally. The env-var route
(`VITE_API_BASE_URL`) is implemented and documented as the alternative, with the
warning that it makes `CORS_ORIGINS` load-bearing.

### The API base URL

It was `const BASE = "/api/v1"` — origin-relative, so **not** hardcoded
localhost, and it already worked through the dev proxy or a single-host rewrite.
I made it `VITE_API_BASE_URL` anyway, defaulting to empty, so a
separately-hosted frontend is a build-time variable rather than a code change.
`frontend/.env.example` documents that Vite inlines it at build time.

### Two security problems I found while doing this

Both matter only if something is publicly reachable, which is exactly the case
task 2 creates.

**The API would have booted in production with `SECRET_KEY=change-me`.** That
value is committed in `.env.example`, so a deploy that forgot to set the secret
would have signed tokens with a publicly known key — anyone could mint an admin
token. `settings.is_production` and `settings.debug` existed and were referenced
nowhere. `app/core/config.py` now refuses to construct settings when
`ENVIRONMENT=production` and the secret is the placeholder, is under 32
characters, or `DEBUG=true`. It raises at import, so the process dies on boot
with a readable message rather than serving. Development is untouched. Five
tests pin it — and they pass `_env_file=None`, without which pydantic-settings
reads the developer's real `.env`, finds a valid secret, and every one of them
passes for the wrong reason.

**The demo accounts.** You offered two options; I took the second, because it is
fail-safe rather than a rule someone has to remember. `export_demo_dump.py`
**excludes the `users` table entirely**, so the shared `ufms-demo-2026` password
cannot reach a hosted instance through the dump even by accident.
`scripts/create_user.py` creates accounts with a 20-character generated password
from an alphabet with no `O/0/l/1/I`, prints it once, and stores only the bcrypt
hash. The local accounts are unchanged and the runbook says explicitly that the
shared password is acceptable locally and only locally.

### `requirements-api.txt`

The API imports `pandas`, `numpy` and `scipy` at boot. That is not accidental
and I did not "fix" it: `dashboard_service.py` recomputes the allocation
correlations and the emerging level-persistence evidence from the stored rows on
each request rather than storing them pre-computed. That is *why* a restored
database reproduces them exactly, and refactoring it four days from a freeze
would be reckless.

But `scikit-learn`, `pyarrow` and `pytest` are never imported by any request
path, and on a 512 MB free instance they are a few hundred megabytes built and
held for nothing. `requirements-api.txt` drops them: **335 MB installed against
473 MB**, and I verified by installing it alone into an empty venv and serving
all five endpoints from it.

---

## 3. The runbook

`docs/03-demo-runbook.md`, written to be executed:

- **Cold start in six steps across three named terminals** — container (wait for
  `(healthy)`; 3307 not 3306), `alembic upgrade head`, restore the dump, create
  accounts, uvicorn on 8000, `npm run dev` on 5173, then the parity check.
- **A failure table**: port already allocated, container not healthy / Docker not
  running, `/health` returning 503, screens rendering with empty panels, login
  422, token expiry, missing geojson, Playwright's missing browser.
- **The five-minute path, with the sentence to say on each screen.** Watchlist is
  **first**, not third — it is already the landing route, so this needed no code
  change. Both caption warnings are repeated in place: never the 14.08% without
  the 4.79% floor and the 37.72% ceiling, and never a trend line on the
  allocation scatter.
- **What is not built**, as a list to volunteer rather than be caught by: no
  alerting loop, no `actual_outcome` written, `interventions` intentionally
  empty, `ground_truth_available: false` and why, no fitted model and why the
  gate killed it, two read-only roles, Delhi unevaluated.

The token expiry row is now a smaller problem than it was: with the token in
`sessionStorage`, **F5 mid-demo is safe**.

One runbook decision worth surfacing: **on demo day, restore the dump; do not
re-derive.** `data/raw/` is gitignored as large and re-fetchable, so a fresh
clone cannot run `python -m app.ingestion.cli derive` at all. That is also why I
**un-ignored `data/processed/demo_data.sql`** and committed it — 612 KB that
turns a clone into a working demo. Tell me if you would rather it stayed out.

---

## 4. The §9 items

**§9.1 — `sessionStorage`, done.** Token in a module variable backed by
`sessionStorage`; every read and write wrapped in try/catch so a browser blocking
site data degrades to the old in-memory behaviour rather than a broken sign-in.
A stored token is only a claim, so `AuthProvider` exchanges it via `/auth/me`
before any screen renders and discards it if the server refuses — which is what
an expired token looks like after an hour. `App.tsx` gates on a `restoring` flag
so a refresh does not flash the login form. I did **not** add a 401 interceptor;
you said keep the expiry handling as it is. Six new tests, including that
`localStorage.length` stays 0. `DECISIONS.md` has the plain-language entry with
the "why not `localStorage`" answer.

**§9.3 — `visual-check` kept**, with `npx playwright install chromium` in the
frontend README under a heading that says a missing browser is a missing browser,
not a broken check. Not wired into CI.

**§9.5 — the basemap stays off, and your one condition was not quite met.** The
tooltip carried ward name, ward number, zone and index — but **not the quarter**.
The quarter was only in the legend below the map, which is fine on screen and
lost the moment a tooltip is cropped into a figure. One line: the tooltip now
reads `Index 1.42, 2025Q1 — …`, and `period` joined the memo's dependency array.

---

## 5. Corrections to the docs

Found while checking claims rather than by looking for them:

- **CLAUDE.md and README said 31 models.** `Base.metadata.tables` has **32**,
  and both databases report 32 base tables besides `alembic_version`. Fixed.
- **CLAUDE.md contradicted itself on `ufms_schema.sql`.** One section said it
  opens with `DROP DATABASE IF EXISTS ufms` and re-running it wipes all data;
  the "Deferred decisions" section said the `DROP` moved to
  `scripts/reset_db.sql` and re-running now fails loudly. The second is true.
  Fixed, with a line saying the old text described the old behaviour.
- The backend README's schema-load command, as above.

I checked queue item 5's concern in passing: `docs/01-evaluation-rules.md` quotes
13.70% only inside the ERA5-basis table and once more explicitly labelled
"ERA5 basis". No document puts it next to 14.08%. The IFS-basis equivalent still
has not been measured; that remains queue item 5.

---

## 6. What I want a second opinion on

1. **Should the deploy be provisioned at all?** It needs three signups, roughly
   an hour of Tanmay's time, and both tiers sleep. Everything technical is done
   and `04-deploy.md` is the click path. My read: the hour is better spent on the
   supervisor conversation, and the deploy is worth doing only if the paper is
   already signed. But it is one line on a slide and you rated it a mark or two.

2. **I did not promote queue item 1 (the memory engine, M0–M3).** The protocol
   says promote the next queue item; the schedule in the same file freezes the
   system on 13–14 September with "no new features". A multi-day modelling task
   does not fit in a four-day freeze window, so I left the queue untouched and
   set the current task to the rehearsal plus the optional deploy. **This is the
   decision most likely to be wrong** — if the ladder is wanted before the 16th,
   say so and I will start it, but something in the schedule has to give.

3. **The backend backlog went out as one commit, not two.** Splitting the
   Alembic work from the derived-tables work would have meant reconstructing
   which model edits belonged to which, with a real chance of a non-building
   intermediate commit. I chose the backup over the history. Reasonable?

4. **Committing `data/processed/demo_data.sql` (612 KB).** It is a generated
   artifact, which argues for ignoring it, but `data/raw/` is ignored too, so
   without it a fresh clone cannot produce a working dashboard at all. I judged
   a self-sufficient repo worth 612 KB. It holds no credentials.

5. **The production config guard is new behaviour, added four days from a
   freeze.** It only fires when `ENVIRONMENT=production`, so it cannot affect the
   demo, and it is covered by five tests. I think it belongs in — a deployed
   instance signing tokens with a committed placeholder is a genuine hole, not a
   tidiness issue. But it is a change to boot behaviour during a freeze window,
   so it should be a conscious call rather than mine alone.

6. **One thing I deliberately did not touch.** `dashboard_service.py` doing
   pandas/scipy work per request is the reason the API needs a 335 MB dependency
   tree and some CPU on every call. On a 512 MB free instance that is the most
   likely cause of a slow or failing deploy. Storing those figures alongside the
   rows would fix it — and it is a change to how every number reaches every
   screen, which is not a thing to do this week. Recording it as a real
   post-freeze item, not proposing it now.

---

## 7. State

- `origin/main` at `33a7ba1`; working tree clean; nothing unpushed.
- 161 tracked files. `.env` untracked and ignored. No `node_modules` or `dist`
  in the index.
- **148 backend tests, 31 frontend tests, `npm run build` clean.**
- `python scripts/check_parity.py --base http://127.0.0.1:8000` → 27/27, PASSED.
- Test scaffolding removed: the parity container is deleted, the throwaway venv
  and the two extra API instances are gone. The local database is unchanged, and
  the probe account I created while testing `create_user.py` was deleted — the
  `users` table holds the same two demo accounts it did before.
