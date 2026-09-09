# REPORT — 10 September 2026 (second session)

Task: do the 15 September rehearsal today, from a fresh clone, as an adversary
of my own documentation; then, if it passed cleanly, queue items 5, 3 and 4.

**The rehearsal passed: a `git clone` reaches a working, correct dashboard with
no manual intervention beyond the documented steps.** Six defects were found on
the way there and all six are fixed. Items 5, 3 and 4 are closed.

Two commits, both pushed:

| | |
|---|---|
| `3ef7d23` | the six rehearsal defects |
| `1773b45` | the IFS re-ranked measurement, and the two register decisions |

`148` backend tests, `31` frontend tests, `27/27` parity, clean tree, nothing
unpushed.

---

## 1. The rehearsal

`git clone` from GitHub into a directory outside the working copy, then
`docs/03-demo-runbook.md` followed literally, against a database created from
nothing.

**The headline result, stated plainly because you asked for it plainly:**

| | |
|---|---|
| Backend tests, fresh clone | **135 passed, 13 skipped** |
| Frontend tests | **31 passed** |
| `check_parity.py` | **27/27 invariants, PASSED** |
| Browser walk of all four screens | **24/24 checks** |

The browser walk is a real Chromium session driving the five-minute path in the
runbook's order. It confirms, in the rendered page: the watchlist is the landing
screen and carries 14.08% **with** 4.79% and 37.72%; the ward index draws the
1.00 reference and **198** ward polygons with **zero** basemap tiles; hovering a
polygon gives `Kempegowda Ward / Ward 1 · Yelahanka / Index 2.19, 2025Q1 — far
above norm` (name, ward, index **and quarter**, which is the §9.5 condition);
emerging says *chronically above norm*, shows the no-ground-truth banner, and
contains "accelerat…" only inside the caveat that rules it out; allocation shows
ρ = 0.474 against ρ = 0.082 and renders the retraction; and there are no console
errors on any screen.

I also tested the runbook's claim that F5 is safe mid-demo. It is: reloading on
`/allocation` keeps both the session and the screen, and a fresh browser context
is **not** signed in — so both halves of the `sessionStorage` rule hold, not just
the convenient half.

### The six defects

**1. The most serious one was invisible, and it is the same shape as the
`_env_file=None` trap you called out in §6.5.**

`tests/test_migrations.py` — the test that proves `alembic upgrade head` and
`ufms_schema.sql` produce an identical `information_schema`, the one that caught
178 differences, the one CLAUDE.md says to run after touching either file — **was
silently skipping on every machine except this one.**

It builds throwaway `ufms_t_*` databases. The `ufms` user that docker-compose
creates owns only the `ufms` database, so `CREATE DATABASE` is denied. On a fresh
clone it skipped with a message; on this machine it ran, because the grant was
there:

```
working copy:   GRANT ALL PRIVILEGES ON `ufms\_t\_%`.* TO `ufms`@`%`
                GRANT ALL PRIVILEGES ON `ufms_base`.*  TO `ufms`@`%`
                GRANT ALL PRIVILEGES ON `ufms_raw`.*   ... and six more
fresh clone:    (none of them)
```

Those were added by hand in earlier sessions and **recorded nowhere**. So the
guarantee was real on one disk and absent everywhere else — and because it
degraded to a *skip* rather than a *failure*, the suite was green while guarding
nothing. `scripts/mysql-init/01-test-grants.sql` now grants it from version
control, scoped to the `ufms_t_` prefix, and runs on first init of the volume. A
fresh clone goes from 129 passed / 19 skipped to **135 / 13**.

**2. `docker compose up -d` fails from a second checkout — and exits 0.**

`container_name: ufms-mysql` was hard-coded while the *port* had an override,
which is an odd asymmetry given the port override exists precisely because
collisions were anticipated. From the clone:

```
Container ufms-mysql Creating
service:db:1 Error response from daemon: Conflict. The container name
"/ufms-mysql" is already in use ...
---exit=0---
```

Exit 0. `docker compose ps` then printed a header and no rows. It is now
`${MYSQL_CONTAINER_NAME:-ufms-mysql}`, the failure table has a row, and the
runbook says to read `docker compose ps` rather than trust the exit code.

**3. The runbook activated the venv once and then opened three terminals.**
Terminal 2 would have met `uvicorn: command not found`. Step 4 now activates it.

**4. A failure row told you to run something that cannot work.** "Map renders
with no ward shading → `python scripts/export_ward_geojson.py`". On a clone that
raises `FileNotFoundError`: it reads `data/raw/bbmp_ward_map_2015.kml`, which is
gitignored. The geojson is committed, so the fix is `git checkout --` on it. The
row said the opposite of the truth.

**5. No failure row for 8000 or 5173 being in use** — including the part people
get wrong, that moving the API off 8000 breaks the Vite proxy target.

**6. Numbers I quoted last session were `information_schema` estimates, not
counts.** `weather_observations` is **1,309,896**, not 1,175,475.
`complaints` is **237,157**, not 234,918 — and that one contradicted CLAUDE.md's
own long-standing figure. `TABLE_ROWS` is an estimate for InnoDB and I used it as
if it were a count. Corrected in the deploy doc, the dump script's docstring and
this report.

### One deviation I had to make, and it is worth knowing

I could not run `docker compose up -d` literally, because defect 2 is triggered
by the working copy's own container, and freeing the name would have meant
stopping the live database. So I applied the fix mid-rehearsal and continued with
`MYSQL_CONTAINER_NAME` and `MYSQL_HOST_PORT` set — which is now the documented
path, so the document was still what I followed.

I then verified the compose change against the **existing populated** database,
because that is the demo path: `docker compose up -d` recreated the container and
every row count matched the pre-change baseline exactly (1,309,896 / 237,157 /
3,960 / 596 / 2). The named volume survives container recreation, which is the
property that makes this safe.

### What the rehearsal did not cover

The clone ran on this machine, with this Docker, this Python 3.12.10 and this
node. A genuinely different machine could still surprise us — but the class of
defect that finds is "missing prerequisite", and section 0 of the runbook is now
the only place that can hide one.

---

## 2. Queue item 5 — the IFS re-ranked baseline is 14.23%

`scripts/measure_reranked_baseline.py`.

Re-ranked means the top-20 is rebuilt **before every test night**, from every
strict event day strictly earlier than that night — so it is handed all the
static list's history plus everything that happened during the test period up to
the previous day. `< night` strictly, because the same day's events are the
label; nothing reads a date on or after the night being scored.

Everything is scored by `score_watchlist` from `app/derived/watchlist.py` — the
same function that produces the 14.08% the API serves — so the comparison is
like-for-like by construction rather than by assertion.

```
basis         days  events    static  re-ranked    delta   oracle   random
era5           138    1289    13.55%     13.70%   +0.14%   37.36%    4.72%
ecmwf_ifs      136    1289    14.08%     14.23%   +0.15%   37.72%    4.79%
```

**The ERA5 row reproduces the published pair exactly.** That is the point of
measuring a basis nobody asked for: 13.55% and 13.70% are already in the docs, so
reproducing both to the quoted precision is what makes the IFS figure comparable
rather than merely new. Had it disagreed, I would have reported the discrepancy
and not published the IFS number.

**Answer: 14.08% → 14.23%, +0.15 points.** Recorded in
`docs/01-evaluation-rules.md`'s IFS table, with the ERA5 pair still beneath it
and labelled. `docs/02-data-profile.md` §14 and CLAUDE.md's Proof One block now
carry a forward reference so neither reads as the current basis.

Two things fell out that are better than the number:

**The re-ranked top-20 changes by a mean of 0.08 wards between consecutive
nights** — about one substitution every twelve nights. That is *why* three
further years of history buy nothing: re-ranking produces very nearly the same
list. It is a more concrete statement of "count-based memory is saturated" than
the 0.15-point delta.

**The 1,289 event count is identical on both bases, and it is a coincidence.**
The two bases share only **126** of their rain days; the 12 ERA5-only days and
the 10 IFS-only days happen to carry **101 events each**. A reader could easily
take the matching totals as evidence that the event set is basis-independent. It
is not — the day sets genuinely differ — and the docs now say so.

**The check you asked for:** no document quotes 13.70% next to 14.08%. Every
mention is inside an ERA5-basis table or explicitly labelled ERA5. CLAUDE.md's
Proof One block quotes 13.7% among 13.6/37.4/4.7, which is internally consistent
ERA5 and now says so.

---

## 3. Queue item 3 — keep `first_listed_year`, leave it NULL

The years do not exist in anything downloadable. I read the schemas of all three
register layers directly rather than inferring:

| Layer | Fields |
|---|---|
| `bbmp_low_lying_areas.kml` | `OBJECTID` |
| `flood_prone_locations.kml` | `OBJECTID` |
| `flood_vulnerable_map.kml` | `OBJECTID, WARD_NAME, WARDNO, LocationName, KGISFVLID, ZONE` |

**No date field in any of them.** The four-digit numbers a naive grep turns up
are coordinate fragments and ids, not years.

So the choice was drop or keep, and I kept it. Two reasons.

It is the socket for the one input that would let Proof Two be validated
externally, and BBMP plainly holds those dates internally — this is an RTI, not a
download. Dropping the column would record "we have decided never to validate
emerging detection", which is a stronger claim than the evidence supports.

And the gap is already *visible* rather than hidden: `/api/v1/emerging` returns
`ground_truth_available: false` and the screen renders it as a banner. A NULL
column plus that banner is a documented gap; a dropped column plus the same
banner is the same gap with the audit trail removed.

I considered a migration to reword the column COMMENT so the emptiness is
self-documenting in the schema, and rejected it: schema churn for prose, three
days from the freeze. Flagging it as an optional post-freeze tidy.

---

## 4. Queue item 4 — leave `is_known_hotspot` FALSE on ward rows

You warned that reading the wrong one widens the pre-specified pool. It does —
confirmed, 42 → 103 — but that turned out to be the fourth-best reason.

**The decisive one: it is not derivable from `locations` at all. Only 200 of the
398 register points carry a `ward_no`**, because only `flood_vulnerable_map.kml`
has a `WARDNO` field. A ward flag computed from the database would be built from
half the register.

**And where the two instruments disagree, the crosswalk is deliberately right.**
The points name 103 wards; `ward_crosswalk.csv` flags 102; the single difference
is **ward 65** — the register calls it `Kadu Malleshwar`, the 2015 delimitation
calls it `Subedarapalya`, and §15.2 left it unpaired rather than guessed.
Populating the flag from the KML's `WARDNO` would silently overrule a recorded
hand judgement. That the two disagree on exactly one ward, and that it is exactly
the one already documented as a hand call, is a good sign about both instruments.

Plus the semantic point: for a point the flag means "on the register", for a ward
the analogous fact is "contains a register point". Overloading one boolean with
two meanings is what caused the confusion originally.

Both decisions are in `DECISIONS.md` in examiner-facing form, including the answer
to "so how do you know the emerging detector works?".

---

## 5. What I want a second opinion on

1. **`scripts/mysql-init/` changes `docker-compose.yml`, three days from the
   freeze.** I judged it in-scope by the same reasoning you applied to the
   production guard in §6.5: the freeze protects the demo path, and this cannot
   reach it — the init script runs only on first initialisation of a volume, and
   the grant is scoped to `ufms_t_%`. I verified `docker compose up -d` against
   the existing populated database and every row count is unchanged. But it is a
   change to the file step 1 of the runbook invokes, so it should be a conscious
   call rather than mine alone.

2. **The `container_name` override is a behaviour change with a default-preserving
   shape.** Unset, everything is exactly as before. I think that makes it safe;
   say so if you disagree and I will revert it to hard-coded and leave only the
   failure-table row.

3. **I did the rehearsal on this machine, not a different one.** That is what was
   asked and it found six defects, but it cannot find a missing prerequisite that
   happens to be installed here. If a second machine is available before the 16th,
   running section 0 on it is the highest-value remaining check — and it is
   ten minutes, not an hour.

4. **`first_listed_year` kept rather than dropped** is the one decision here I
   could argue either way. The case for dropping: a permanently-NULL column is
   schema noise and an examiner may ask why it exists. The case for keeping, which
   I went with: it names the missing input. If you prefer dropped, it is a
   migration plus a model edit plus `ufms_schema.sql`, and it should happen before
   the 13th or not until after the 16th.

5. **Nothing else is queued for this week, and I think that is correct.** What
   remains is Tanmay's: the supervisor on the 14th, names on the paper and slides
   1 and 14, and the reference volume and page numbers. The system is done and
   rehearsed.

---

## 6. State

- `origin/main` at `1773b45`; working tree clean; nothing unpushed.
- 164 tracked files. `.env` untracked and ignored.
- **148 backend tests** (working copy), **135 passed / 13 skipped** (fresh clone),
  **31 frontend tests**, `npm run build` clean.
- `python scripts/check_parity.py --base http://127.0.0.1:8000` → 27/27, PASSED.
- `scripts/measure_reranked_baseline.py` reproduces 13.55 / 13.70 / 14.08 / 14.23
  on demand.
- Rehearsal artifacts removed: the clone's container and volume are gone
  (`docker compose down -v`), and the clone's contents are deleted. Its now-empty
  directory in `%TEMP%` would not unlink — some Windows process still holds the
  handle — so it is 4 KB of empty directory in the OS temp area rather than truly
  zero. Saying so rather than claiming a clean sweep.
- The working copy is untouched: the same container, the same named volume, row
  counts byte-for-byte identical to the pre-rehearsal baseline (1,309,896 /
  237,157 / 3,960 / 596 / 2), and the same two demo accounts.
