# NEXT — the work queue

**How to use this file.** Read it, do the task under "Current task", then move
that block into "Done log" with the date and a one-line result, and promote the
next item from "Queue". If a task's spec turns out to be wrong or impossible,
stop and say so rather than improvising around it.

**Reporting protocol — this matters, please follow it exactly.**

When you finish a task, write your full report to `REPORT.md`, overwriting
whatever is there. Do not summarise it into the chat and expect a human to
carry it anywhere. A second Claude reads `REPORT.md` directly off disk, decides
what happens next, and writes the answer back into this file. The user is not a
message bus and should not have to paste anything between the two of you.

Write `REPORT.md` for that reader, not for a person skimming: full numbers, the
reasoning behind judgement calls, anything that contradicted the spec, and an
explicit list of what you want a second opinion on. Length is fine. Being
readable without the surrounding conversation is what matters.

Then say one line in the chat — "done, report written" — and stop.

Standing rules live in `CLAUDE.md` and `docs/01-evaluation-rules.md`. Read both
before starting anything here.

---

## HARD DEADLINE: 16 SEPTEMBER 2026 — seven days

**This is a PROGRESS evaluation, not the final.** That changes the balance
completely.

| Component | Marks | What it actually needs |
|---|---:|---|
| Project completion + working model | 20 | Progress demonstrated. What already exists — 31-table schema with migrations, 1.3M weather rows, 237,157 complaints, five working endpoints, four working screens, 143 backend + 25 frontend tests — is already a substantial showing. |
| **Research paper** | **30** | A completed written paper, a named target conference, supervisor approval. **Zero if absent.** |

**The paper is the priority. The frontend is not do-or-die.**

Progress reviews ask three questions: what have you built, what have you found,
what is left. You have unusually strong answers to all three — the found part in
particular, since most projects at this stage have a model and no idea whether it
means anything.

---

## Current task — the residual, and it is small

**All three items of the previous task are done, except the part that needs an
account. Read `REPORT.md` before deciding anything here.**

The previous task's three items landed as follows:

1. **Frontend into version control — done, and it was worse than described.**
   The frontend was untracked, and the *backend* was 13 commits and a 48-file
   working tree ahead of a remote that only had Phase 0. Both are now pushed.
2. **Deploy — prepared and proved locally, not provisioned.** Everything up to
   account signup is done and verified end to end. The signup is not something
   Claude can do.
3. **Runbook — done.** `docs/03-demo-runbook.md`, plus `docs/04-deploy.md`.

### What is left, in priority order

**1. Rehearse from the runbook on 15 September.** Follow
`docs/03-demo-runbook.md` literally on the demo machine, change nothing, note
every place it fails. This is the single highest-value system task remaining.
Start with `python scripts/check_parity.py --base http://127.0.0.1:8000` — it
must print `27/27 checks passed`.

**2. Provision the deploy, if it is still wanted — Tanmay only, ~1 hour.**
`docs/04-deploy.md` is the click path. Three signups, none needing a card:
Aiven (MySQL, free, 1 GB), Render (API, free), Vercel (static). The one step
that was not verifiable without an account is Aiven's TLS against PyMySQL, and
it is flagged in the doc with the error to expect. **Stop if a card is asked
for, or after roughly three hours.** The demo runs from localhost regardless.

**3. Nothing else, until the paper is signed.** See below — the paper is 30
marks and the supervisor conversation cannot happen on the 15th.

### A judgement call, flagged for whoever writes this file next

I did **not** promote queue item 1 (the memory engine and the model ladder
M0–M3) into the current task, even though the protocol says to promote the next
queue item. Building the ladder is days of work, and the schedule in this file
freezes the system on 13–14 September with "no new features". Promoting it would
have put a multi-day modelling task into a four-day freeze window.

The queue is therefore untouched. If that is wrong, say so and I will start it.


## The paper and the deck exist. Do not write either one here.

Both are drafted in the planning session — `UFMS_paper.docx` (9 pages, IEEE
structure) and a 15-slide progress deck with speaker notes. Two versions would
diverge. The nine figures you produced are going into the paper from the
planning session side.

---

## Revised schedule

| Date | System | Paper and documents |
|---|---|---|
| **9-10 Sep** | Frontend into git and pushed; deploy attempt | Paper drafted — **done** |
| **11-12 Sep** | Runbook; buffer for whatever the deploy broke | Paper revised; **supervisor approval**; conference named |
| **13-14 Sep** | Freeze. No new features. | Deck finalised — drafted, needs names |
| **15 Sep** | Rehearse from the runbook, on the demo machine, changing nothing | Print and assemble |
| **16 Sep** | Evaluation | |

---

## Only Tanmay can do this, and it is this week

The paper and deck are drafted, so what is left on them is not writing:

- Author names, institution and supervisor on the paper and on slides 1 and 14.
- Verify the reference volume and page numbers before submission.
- **Talk to the supervisor.** Option (b) needs their consent and a named target
  conference; neither can happen on the 15th.

That conversation is also the one flagged three sessions ago: the results are
measured limits, not a working predictor. The supervisor needs to know that
before signing, not after. `DECISIONS.md`, first three entries, ten minutes.

---

## Queue

**1. Memory engine and the model ladder M0-M3** - to demonstrate the bound, not
to beat it. Report within-night AUC or precision@k, never a pooled AUC.

**2. Hotspot register dedup decision.** Three KML layers loaded unmerged.

**3. `locations.first_listed_year` is NULL for all 398 register points** —
the KML carries no year. Drop the field or source the years elsewhere.
**Now also blocks the emerging screen's only external validation**, which is
why `/api/v1/emerging` returns `ground_truth_available: false`.

**4. `locations.is_known_hotspot` is FALSE for all 198 ward rows.** The flag is
set on the 398 register points only, so the ward-level register fact lives in
`ward_crosswalk.csv` and `app/derived/emerging.py` reads it from there. Decide
whether the ward rows should carry it; reading the wrong one would widen the
pre-specified emerging pool from 42 wards to all 103.

**5. Measure the re-ranked baseline on the IFS basis.** Drafting the paper
surfaced a basis mix of the kind you caught in §17.3: the "same list, re-ranked
on all prior history" figure of **13.70%** is an ERA5 number, and it was sitting
in a table whose other five rows are IFS. It has been removed from the paper's
Table II and the observation is now stated as an ERA5-basis pair (13.55% →
13.70%), which is at least internally consistent. But the IFS-basis equivalent
of 13.70% has never been measured. Measure it, record it in
`docs/01-evaluation-rules.md` beside the other IFS figures, and check whether
any other doc quotes 13.70% next to 14.08%.

**6. Re-run the drainage classification off the YAML** instead of keywords.
Note this is now cosmetic: profile §28 closed effectiveness for good, so a
better drainage classifier changes a descriptive spend figure, nothing more.

## Done log

- **2026-09-10 — Everything is in version control and pushed; the demo is
  runbookable; the deploy is proved locally but not provisioned.**
  **The backup gap was bigger than the frontend.** `ufms-frontend/` was indeed
  untracked, but `origin/main` was still on **Phase 0** — 13 unpushed commits
  plus a 48-file working tree holding all of Phases 1–4. Both are pushed now;
  `git status` is clean, `origin/main..HEAD` is empty, `.env` is untracked and
  ignored. The frontend moved to `frontend/` as a plain directory move, verified
  by file count (45 files staged, zero from `node_modules` or `dist`) rather than
  by trusting the ignore pattern. `scripts/export_ward_geojson.py` now writes
  inside the repo and **reproduces the committed geojson byte-for-byte** from the
  new path; `paper-figures.mjs` writes to `docs/figures/`.
  **The deploy design note is verified, not assumed.** The API's table closure is
  nine tables and 4,820 rows — it never reads `weather_observations` (1.18 M
  rows, 146 MB) or `complaints` (235 K, 64 MB) — so the dump is **612 KB against
  a 215 MB database**. A fresh MySQL built by `alembic upgrade head` plus that
  dump, served from a clean venv holding only `requirements-api.txt`, in
  production mode, returned **byte-identical JSON on all five endpoints** to the
  full local instance, and 27/27 frozen invariants on both.
  `scripts/check_parity.py` is that check and doubles as the pre-demo smoke test.
  **Providers checked this week**: Aiven always-free MySQL (1 GB, no card) and
  Render free web services (no card) both still exist; **both sleep**, which is
  why the runbook says localhost regardless. Not provisioned — that needs signup.
  **Two security fixes for anything publicly reachable**: the API now refuses to
  boot when `ENVIRONMENT=production` and `SECRET_KEY` is the placeholder
  committed in `.env.example`, is under 32 characters, or `DEBUG=true` (it raised
  nothing before, so a forgotten secret would have signed tokens with a publicly
  known key); and the dump **excludes `users`** so the shared local demo password
  cannot be published, with `scripts/create_user.py` seeding generated passwords
  instead.
  **§9 answers actioned**: token moved to `sessionStorage` with `/auth/me`
  restore and a `DECISIONS.md` entry; `npx playwright install chromium` in the
  frontend README; the choropleth tooltip now carries the quarter as well as the
  ward name and index, which was the one §9.5 condition not already met.
  **Doc errors found and fixed**: CLAUDE.md and README said 31 models where the
  metadata maps 32; CLAUDE.md still claimed `ufms_schema.sql` opens with
  `DROP DATABASE`, contradicting its own later note; the backend README's
  schema-load command pointed at `../ufms_schema.sql` and omitted
  `--default-character-set=utf8mb4`. **148 backend tests and 31 frontend tests
  pass.**

- **2026-09-09 — Phase 4: the frontend is built, and the watchlist context is
  structural rather than adjacent.** `ufms-frontend/`, React 19 + Vite 8 +
  Tailwind v4 + Recharts + Leaflet. Four screens, login with the token in
  memory only, both roles read everything, no mutation UI. **The Screen 2
  instruction was right and it worked**: precision@20 is a mark on a scale that
  ends at the oracle ceiling, with the chance floor as a region of the track, so
  neither reference point can be removed without breaking the drawing. The bar
  is split at the floor rather than filled from zero — filling from zero hid the
  chance region under its own fill, which was visible only on a screenshot.
  **25 frontend tests pin the rules in the rendered DOM**: all three figures
  present and ordered floor < achieved < ceiling, an unscored snapshot showing a
  blank rather than a borrowed number, the emerging label never "accelerating"
  outside the caveat that rules it out, `ground_truth_available: false` as a
  visible banner, the retraction rendered in full, and "dose-response" appearing
  nowhere outside the block that retracts it.
  **A fifth endpoint was needed and added**: `GET /api/v1/index` returns every
  ward's index for one quarter, because a choropleth assembled from 198 per-ward
  calls renders half-shaded when one fails, and an uncoloured ward reads as
  "nothing happened here". **Ward polygons are generated** by
  `scripts/export_ward_geojson.py` (198 wards, 661 KB, fails loudly on anything
  but exactly 198). **The map ships with no basemap**: CARTO now watermarks
  every tile "API KEY REQUIRED", and a road basemap under a diverging
  choropleth competes with the encoding anyway.
  Palette validated in both modes before any chart code was written; the dark
  meter track had to be re-stepped from #184f95 to #17304f because at full
  saturation it read as a third filled segment. `npm run visual-check` walks the
  four screens at 390/768/1360 and fails on a console error or a sideways
  scroll — it found five real defects on its first run, none of them visible
  from the DOM.
  **Figures delivered** to `docs/figures/`, nine of them at 2×, rendered from
  the live system with a manifest naming the numbers in each.
  **Docs done as instructed**: `docs/01-evaluation-rules.md` restated on the IFS
  basis (4.79 / 14.08 / 37.72 leading, ERA5 4.72 / 13.55 / 37.36 beneath and
  labelled, conclusions stated as unchanged); profile §17.4 records that 4.80%
  was a simulated estimate of the analytic 4.79%; profile §25.1 now names the
  test behind every p-value in the persistence claim (Mann-Whitney U 0.00014,
  Wilcoxon signed-rank 0.116 — **the 0.23 could not be reconstructed because its
  test was never recorded**, so 0.116 is the figure to quote); `CLAUDE.md`
  records that `interventions` is intentionally empty.
  **143 backend tests and 25 frontend tests pass.**

- **2026-09-09 — The four derived tables and their endpoints. All four
  reconcile exactly.** `ward_quarter_index` (3,960 ward-quarters, 198 wards x
  20 quarters, `city_share` stored beside every row so `rel` needs no second
  pass), `watchlist_snapshots` + `watchlist_entries`, `emerging_watch` (103
  eligible wards) and `ward_allocation` (110 wards, 103 treated). Migration
  `270818598e13`; `ufms_schema.sql` section 7; `alembic check` clean and
  `test_migrations.py` still green. **Reconciliation at 1e-9 against all three
  reference CSVs**: the index reproduces `ward_dose_response_panel.csv`
  (pre, post, ev_pre, ev_post, ev_all) and `ward_relative_trends.csv`
  (rel_first4/last4, events, co_first4/last4, and the raw/share/rel Theil-Sen
  slopes with their Mann-Kendall p-values); `emerging_watch` reproduces
  `ward_persistence.csv` on all six columns; `ward_allocation` reproduces spend
  and area **recomputed from the 198 raw work-order CSVs**, not copied — 45,737
  main + 4,178 legacy rows, 16,648 drainage matching the YAML's `union_rows`,
  1,353 + 125 in window, Someshwara Rs 631,617,283 to the rupee. The watchlist
  reproduces the frozen top-20 in rank order and precision@20 = 14.0809%,
  oracle 37.7206%. **Two spec corrections.** (1) The brief's context triple
  mixes bases: 14.08% and 37.72% are the IFS/136-day basis (§17.3 variant B)
  but **4.72% is the ERA5/138-day basis**, which pairs with 13.55% and 37.36%.
  Measured on the IFS basis the random floor is **4.79%** and that is what is
  stored; profile §17.4's 4.80% is the same number from a simulated draw.
  (2) `locations.is_known_hotspot` is FALSE for all 198 ward rows — the flag is
  set on the 398 register points — so the register flag comes from
  `ward_crosswalk.csv`; reading it from `locations` would have marked all 103
  eligible wards off-register and widened the pre-specified pool. Also found:
  `ward_allocation.event_days_total` must be events over all 20 quarters, not
  pre+post, or the targeting partial correlation moves from -0.050 to +0.018.
  Endpoints `/api/v1/index/{ward}`, `/watchlist`, `/emerging`, `/allocation`,
  all GET, both roles, caveats and the retraction carried as response fields.
  `test_migrations.py`'s statement splitter was cutting `CREATE TABLE` in half
  on a semicolon inside a column COMMENT; it is quote-aware now. **135 tests
  pass**, up from 72.

- **2026-09-08 — The gate failed; analysis closed permanently. Migrations
  live.** **Within-ward identification is impossible on this data and no model
  was fitted.** Staggered timing does not exist: **zero** wards have their
  first-ever drainage work inside 2021Q1-2022Q4 (all 196 with dated works were
  first treated 2011-2014), the median ward had works completing in **6 of the
  8 quarters before** the window, and only **4 of 8** quarters carry ≥5
  first-treated wards against a ceiling of 8. Ward work profiles correlate with
  the citywide calendar at **ρ = +0.505**, and the work-order file stops at
  2023Q1 while the outcome panel runs to 2025Q1 — **40% of the "post" period is
  censoring, not absence of treatment**. The intensity anchor does not rescue
  it (6 of 8 quarters, but 51 of 196 wards peak *below* their own norm). New:
  **5 of the 7 "untreated" wards had ₹37-121 M of drainage work before the
  window**, so the treated indicator (-0.4497, p = 0.0084) is not a
  treated-vs-control contrast either and must not be used as a fallback.
  Profile §28. The surviving effectiveness output is the allocation finding,
  plus its companion, in the scoped wording: drainage works are distributed
  continuously and near-uniformly across all 198 wards since 2013, so **no
  observational evaluation of their effect is identifiable from these
  records** - the treatment does not vary enough for any design to exploit.
  **Alembic bundle done**: baseline against an empty database + the 3 views by
  `op.execute`, then `weather_cells.model` and `ward_period_totals`; dev
  stamped, `alembic check` clean. Verifying it found **178 differences between
  the models and `ufms_schema.sql`** — every FK and 27 indexes named by MySQL
  rather than the schema, 23 missing server defaults, 7 TIMESTAMP columns
  turned DATETIME, `users.updated_at` missing `ON UPDATE CURRENT_TIMESTAMP`,
  all 25 column comments dropped — all fixed, and now pinned by
  `tests/test_migrations.py`, which builds a database each way and diffs
  information_schema. `ward_period_totals` is populated (4,356 rows, matching
  the CSV exactly). 72 tests pass.
- **2026-09-07 — Phase 0 verified.** Docker MySQL on 3307, schema loaded (26
  tables + 3 views), API boots, `/health` reports reachable, 5 security tests
  pass. Fixed: port conflict, missing `email-validator`.
- **2026-09-07 — Data profile.** 766,648 grievance rows across six CSVs, nine
  raw files. Five findings that changed the loader design: lost AM/PM marker,
  84% of waterlogging signal outside the SWD category, ward join failure,
  status vocabulary drift, literal `null` strings.
- **2026-09-07 — Rainfall loader.** 512,568 hourly rows, 9 cells, 2019-01-01 to
  2025-06-30, aggregated to 21,357 cell-days. Expanding-window percentiles
  pinned by tests. Annual totals reproduce known years.
- **2026-09-07 — §13 reporting lag.** Lag 0 is correct; lag 1 is
  indistinguishable from noise (p = 0.695) and lags 2–3 are worse. The 3-day
  window's higher lift is denominator-driven, not a better detector.
- **2026-09-07 — §14 Proof One baseline.** Static top-20 = **13.55%**
  precision@20; re-ranked on more history = 13.70% (no gain); oracle ceiling =
  **37.36%**; random = 4.72%. Frozen top-20 is the Outer Ring Road belt.
- **2026-09-07 — Ward crosswalk.** `data/reference/ward_crosswalk.csv`, 198
  rows: 55 `exact`, 20 `normalised`, 27 `manual`, 96 `not_in_register`, **0
  `unresolved`**. 102 wards mapped to a ward number = 59.69% of complaint rows;
  **0 rows excluded**. Two spec corrections, see §15.2: the artifact has 198
  rows not 103 (103 is the register-side count), and `match_method` needed a
  fifth value `not_in_register` — treating those 96 wards as `unresolved` would
  have silently dropped 309,012 rows (40.31%). Register ward 65
  `Kadu Malleshwar` left unpaired rather than guessed. Loader rule +
  21 tests in `app/ingestion/ward_crosswalk.py`, `tests/test_ward_crosswalk.py`.
- **2026-09-07 — Per-ward recompute (§16). The prediction was wrong.**
  Crosswalk rebuilt on `bbmp_ward_map_2015.kml` (the 198-ward delimitation):
  **all 198 wards** now carry a ward number, centroid, zone and area — 100% of
  complaint rows, up from 59.69%. All 102 register-derived numbers agree with
  it, independently confirming the §15 hand calls. `locations` holds 198 ward
  centroids + 398 register points, every one with a `cell_id`.
  **But 176 of 198 wards (89%) share one ERA5 cell** — the grid step (~22 km)
  is barely finer than the city (~30 km). Per-ward rainfall therefore moves
  lag-0 lift 3.06 → 2.89 (χ², p = 0.575) and precision@20 13.90% → 13.01%
  like-for-like: slightly **worse**, not better. §12.6's caveat is retired, the
  headline baseline is unchanged, and the finding bounds M1/M2 — ERA5 cannot
  discriminate between wards on the same night, so whatever does must come from
  memory and terrain. 46 tests pass.
- **2026-09-08 — Finer rainfall tested; KSNDMC investigated.** `ecmwf_ifs`
  (~9 km) resolves BBMP into **14 cells** against ERA5's **3** (modal cell 28%
  vs 79%, 2.8x the across-ward spread), so the backfill ran: 797,328 hourly
  rows, 2019-2025, all 198 wards reassigned. **Per-ward rainfall still changes
  nothing** — lag-0 lift 3.06 -> 3.00, chi2 **p = 0.877**; the precision@20
  restriction still costs -6.0%. The hypothesis is now tested and rejected at
  9 km, not merely untestable. `era5_land` is unusable (NULL precipitation).
  **New headline finding (§17.4): a weather-only ranking scores 5.63% against a
  4.80% random baseline, while memory alone reaches 14.08% and the ceiling is
  37.72% — weather alone ranks at chance**, and the finer model scores *lower*
  than the coarse one. Added to `docs/01-evaluation-rules.md`; expect M1 ~5%.
  **KSNDMC: 131 gauges inside BBMP, median 0.95 km per ward — but only 5 report
  to the national portal and only from Aug 2023, and the advertised 1991-2020
  file is 342 bytes.** Dead end without an RTI. 57 tests pass.
- **2026-09-08 — Headroom tested. It is not reachable.** A ward-level ranking
  fitted with **perfect foresight** of the test period reaches **15.66%**
  against the honest **14.08%** — so only **1.58 of the 23.64 points (6.7%)** of
  headroom is ward-level at all; **93.3% is within-ward temporal variation**.
  Consecutive rain nights' event vectors correlate at **0.090**. 70.3% of events
  are surprises, median prior-rank 69, only 0.8% from cold wards — so the static
  list is not merely cut too short (top-40 captures 46% at precision 10.92%).
  **The prescribed FMI interaction features were built and tested and are worse
  than memory alone** (cond_rate 12.94%, +excess 12.79%, vs prior_n 14.08%);
  they correlate with plain prior count at r = 0.85-0.88. Terrain and elevation
  add nothing. **New trap named: pooled ROC-AUC 0.749 coexists with +0.18
  points on precision@20 (p = 0.84)** because rainfall carries 74-100% of its
  variance between nights while precision@k compares within a night — rule added
  to the evaluation rules. Proof One flagged for restatement. Profile §19;
  `data/reference/ward_elevation.csv` added. 57 tests pass.
- **2026-09-08 — Night size: weakly predictable, and only at the extremes.**
  On the target as specified (raw count of wards with an event per rain day)
  weather **fails**: R2 = -0.03, worse than predicting the test mean, because
  reporting volume roughly doubles across the window and correlates with time
  (0.243) as strongly as with rainfall (0.214). Re-run against a trailing-90-day
  baseline — **a change to the brief, flagged** — weather reaches **R2 = 0.196**
  (95% CI 0.082-0.278) and 3-class accuracy **50.0% vs 39.6% majority**
  (+10.5 pts, CI [-0.8, +20.5], model wins 96.1% of bootstraps). The pre-set bar
  (R2 > 0.4, or 3-class meaningfully above majority) is **missed on the first,
  marginal on the second**. Genuinely useful only at the top: binary "worst
  third" AUC **0.749**, and **9 of the 10 most confident nights were severe**
  against a 26.5% base rate; the middle of the distribution is near chance.
  Verdict: *unpredictable in location, weakly predictable in magnitude, reliable
  only for the worst nights.* Advisory output, not a headline.
  **Label ceiling bounded (§21):** 16 of the frozen top-20 wards are on BBMP's
  agency-observed register against a 52% base rate (hypergeometric p = 0.006),
  but severity agreement is only moderate (Spearman 0.334, 9/20 list overlap).
  The label finds real places; its error is in **timing and degree, not place** —
  converging independently with §19.6. Proof One restated in the rules file;
  five settled decisions recorded. 57 tests pass.
- **2026-09-08 — Reporting growth would have made Proof Two all false
  positives.** Complaint volume doubled 2021-2024 (2.00x citywide) and ward
  growth is **not uniform**: p10 1.42x, p50 2.00x, p90 3.00x, range 0.87x-4.81x,
  p90/p10 = 2.12x. Theil-Sen + Mann-Kendall on 20 quarters, 103 eligible wards:
  **raw event counts give 7 significantly rising wards; normalised by each
  ward's own complaint volume, 0** — under all three denominators tested (all
  complaints / stable categories / solid-waste-only, agreeing at rho 0.85-0.995)
  — while **10 decline significantly**. Raw-vs-normalised slope correlation is
  only 0.394; top-20 overlap 11/20. **Bellandur and Varthur sit in the raw top
  11 purely on volume growth.** Growth is **not socially patterned** (SC+ST share
  rho = -0.057, p = 0.42; no core/periphery effect) — a noise problem, not an
  equity one. The four register-absent wards checked by name: **Jakkur ranks #1
  on raw growth** (3.11x volume, p = 0.183 normalised) and **Hoodi is
  significantly *declining*** (p = 0.007) despite 3.06x volume growth — so
  "absent from the register" means the register is stale, not that the ward is
  worsening. **After correct normalisation there is no emerging signal at ward
  level at all** (closest p = 0.139, in a test that finds ten declines) — likely
  a granularity wall, since the complaints carry no sub-ward geography.
  **Both proofs are now negative-shaped; see REPORT.md §6 for the options.**
  New: `ward_socioeconomic.csv` (population, SC/ST, density from the BBMP 2014
  delimitation file), `ward_growth_trends.csv`. 57 tests pass.
- **2026-09-08 — Proof Two is alive; the null was wrong. Work orders feasible.**
  Testing each ward's normalised slope against **zero** was wrong because the
  citywide share itself fell 22%. Benchmarked to the city trend
  (`events / (complaints x city_share)`, a standardised incidence ratio) the
  same data gives **9 rising / 4 declining** instead of 0 / 10. A permutation
  null (2,000 draws, shuffling quarters within ward) expects 2.4 risers and
  observed 9 — **p = 0.0010**, so the aggregate signal is real. **But BH-FDR
  leaves 0 nameable wards over all 103, and exactly 1 — Jakkur — under the
  pre-specified non-register pool (q <= 0.10)**; split-half slope correlation is
  0.035. Real in aggregate, barely identifiable per ward — the third time this
  project has landed on that shape. **Question 3 settled:** all four correct-null
  decliners fell in absolute terms while the city rose 78%, so improvement is on
  the table for Bagalagunte, A.Narayanapura, Padmanabha Nagar and Ramamurthy
  Nagar — whereas 4 of the 10 zero-null "decliners" had absolute events *rise*
  (Hoodi 25->32, Horamavu 43->46, Varthur 15->27). **Work orders: feasible.**
  ~1,350 usable drainage works across 166 wards (2021-01..2022-12), ward/cost
  100%, dates 95%, drainage separable at 36.4% of 45,737 rows. Wards 184-198 use
  a legacy dateless schema and are unusable as-is. Only 32 untreated wards, so
  **dose-response on spend**, not treated-vs-control. Jakkur is the 2nd-highest
  drainage spender (Rs 494M) *and* the one FDR-surviving riser — a ready-made
  case study. New: `ward_relative_trends.csv`. 57 tests pass.
- **2026-09-08 — Intervention effectiveness: the one positive result.**
  Dose-response of the change in relative flooding index on log drainage spend:
  **coefficient -0.0240, se 0.0096, p = 0.0138, 95% CI [-0.0428, -0.0052],
  n = 110 wards**, controlling for pre-period index and log ward area. R2 0.531.
  **Reverse causality is measurably absent** - corr(pre-period index, log spend)
  = -0.083, p = 0.39; spend tracks **ward area** (rho +0.474) and raw counts
  (+0.355) but not relative flooding need, and only 20% of works sit under
  per-ward budget heads, so allocation is discretionary yet still untargeted.
  Residualising spend changes nothing because there is nothing to residualise.
  **But the response is NOT monotone**: quintile deltas +0.232, +0.108, -0.146,
  -0.162, **+0.105**, untreated +0.251 - the top spend quintile got worse and
  the coefficient is carried by Q1-Q4. Never publish it without that table.
  **Jakkur: the spend came first** - Rs 346M in 2020 and Rs 494M in 2021-22 while
  the index went 0.55 -> 0.93 -> 1.42; first spend 2020Q2 against first
  above-norm quarter 2021Q2, cross-correlation negative at every lag. "Works as a
  response to deterioration" is unsupported there (caveat: work-orders data ends
  2022, so later blanks are censoring). **§24's register-contradiction claim is
  RETRACTED** - across all 198 wards p = 0.789, top-20 enrichment p = 0.713; it
  was a four-ward coincidence. **Persistence instrument corrected**: level, not
  slope - top-10 slope-flagged wards end at mean index 1.77 vs 1.16 for all
  wards, 10/10 above the city norm, p = 0.0001, and slope-flagging beats
  level-flagging (1.77 vs 1.45). The detector finds *chronically above norm*,
  not *accelerating*. **Wards 184-198 recovered** via BR date (validated: +22d
  median offset, 76.2% within 90d), adding 125 drainage works. New:
  `ward_dose_response_panel.csv`, `ward_persistence.csv`. 57 tests pass.
- **2026-09-08 — Analysis closed. Q5 was never a reversal.** Both explanations
  tested and rejected: **development** (corr(log spend, log volume growth)
  = -0.112, p = 0.243; Q5 median growth 1.98x vs Q1's 1.94x; adding the control
  moves the coefficient -0.0240 -> -0.0247) and **disruption** (Q5 2024-25 vs
  2023 = -0.030, p = 0.834; spend coefficient stable at -0.0243 on 2023 and
  -0.0238 on 2024-25). The premise was wrong: **only the lowest-spend quintile
  differs from zero** (Q1 +0.232, p = 0.022; Q5 +0.105, CI [-0.142, +0.353],
  p = 0.385), and a quadratic term in log spend is not significant (F = 1.26,
  p = 0.265). §25.5 over-read its own table; corrected in place because it
  carried an *instruction* that would have propagated a wrong emphasis.
  **Targeting objection settled**: spend vs absolute events is +0.274 raw and
  **-0.050 (p = 0.603) controlling for ward area** - area fully explains it
  (spend vs area +0.474, events vs area +0.649). "BBMP targets absolute
  complaint volume" is dead, not deflected. **One deflation recorded**: the
  effect is significant conditional on controls, not raw (Spearman -0.163,
  p = 0.099); the main spec gets there by controlling for mean reversion
  (-0.788), so a raw scatter looks weak. 57 tests pass.
- **2026-09-08 — Complaints loaded; effectiveness outcome claim retracted.**
  `hazard_categories.yaml` built (9 waterlogging sub-categories split event 3 /
  maintenance 6, Solid Waste 13, 4 documented exclusions, 9-value status map,
  work-order patterns, every entry carrying its row count). Loader: **237,157
  complaints** upserted of 766,648 read - WATERLOG 42,004, GARBAGE 195,153,
  event 8,293, maintenance 33,711, exactly the YAML totals, idempotent.
  **The reconciliation test passes exactly**: the database rebuilds the relative
  index matching `ward_dose_response_panel.csv` to < 1e-9 across all 110 wards,
  same event counts, 9 assertions. It surfaced one design gap - the denominator
  is the ward's TOTAL complaints, which rule 7 forbids loading, so it is
  persisted as `ward_period_totals.csv` (4,356 rows) pending a table.
  **Then the added-variable plot retracted §25's headline.** Refitting on
  treated wards only: **-0.0064, p = 0.833** against the published -0.0240
  (p = 0.0138). `log1p(spend)` put 7 untreated wards at 0 against treated wards
  at 16-20, so the slope was fitted through two clusters; a bare treated
  indicator (-0.4497, p = 0.0084) is *stronger* than the dose. Those 7 wards are
  the ones §25.2 had already ruled out as a control group and their own mean is
  insignificant (CI [-0.778, +1.280]). **No dose-response exists.** New rule:
  refit any dose-response on treated units only before reporting it. The
  ALLOCATION finding survives untouched - spend tracks ward area (rho +0.474),
  not flooding need (r = -0.083). 66 tests pass.
