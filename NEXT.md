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

## Current task — `data/reference/hazard_categories.yaml`

Hand-curated map from exact source category and sub-category strings to
`WATERLOG` / `GARBAGE`, and within waterlogging to `event` vs `maintenance`.
Preserve source strings byte-exactly; note the double space in
`Storm  Water Drain(SWD)`. Record the row count beside each entry so vocabulary
drift shows in a diff. A citable methodological artifact, not a config file.

Profile §10.1 has the counts and the parent-category table; §12.4 has the
event/maintenance evidence (rain lift 3.07x for `water stagnation` against
1.33x for `Road side drains`).

---

## Queue

**1. Housekeeping bundle — fell off the queue, put it back.** Agreed two rounds
ago, never scheduled. (a) Restate the §12-§14 headlines on IFS: 13.55% -> 14.08%
static baseline, 37.36% -> 37.72% ceiling, 4.72% -> 4.79% random, keeping ERA5
as a labelled before/after. The seam is now *internal to the profile* - §12-§14
quote ERA5 while §17-§21 quote IFS. (b) Baseline Alembic against an empty
database, hand-add the three views with `op.execute`, verify a fresh
`alembic upgrade head` matches loading `ufms_schema.sql`, `alembic stamp head`
on dev, then add `weather_cells.model` as the first real migration and backfill
it (cells 1-9 `era5`, 10-23 `ecmwf_ifs`).

**2. Complaints loader.** `app/ingestion/bbmp_complaints.py`, driven by the
hazard YAML. Idempotent on `Complaint ID`. Truncates timestamps to DATE
deliberately. Applies the crosswalk, keeps `in_flood_register=false` wards in
the panel, logs excluded counts unconditionally.

**3. Hotspot register dedup decision.** Three KML layers already loaded
unmerged (398 points, `hotspot_source` per layer). Establish what each layer
represents before choosing a threshold.

**4. Model ladder M0-M3 — to demonstrate the bound, not to beat it.**
All four landing near 14% against a 37.72% ceiling is the result. Report
within-night AUC or precision@k, never a pooled AUC.

**5. Learn outputs — emerging detection and intervention effectiveness.**
These now carry the project (Proof One restated). Untouched by the §19 result:
they use accumulated ward history, not nightly ordering. Profile §21 notes that
Hoodi, Someshwara, Jakkur and Basavanapura are top-20 complaint wards *absent*
from the official register - emerging candidates surfaced unprompted.

**6. Magnitude advisory output (optional, after the Learn outputs).** Profile
§20: AUC 0.749 on "is tonight in the worst third", 9 of the top 10 flagged
nights genuinely severe. Needs a maintained trailing baseline. Weak in the
middle of the distribution. Build only if the Learn outputs land early.

## Done log

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
