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

## Current task — complaints loader

`app/ingestion/bbmp_complaints.py`, driven by
`data/reference/hazard_categories.yaml`. Idempotent on `Complaint ID`.
Truncates timestamps to DATE deliberately — the source lost its AM/PM marker,
so any time-of-day value would be fiction. Applies the crosswalk; logs excluded
rows.

**Dependency: this needs the hazard YAML, which is the next queue item.**
Either build the YAML first and treat both as one task, or reorder the queue.
Flagging rather than deciding.

Everything else it needs is in place: all 198 ward names resolve to a BBMP ward
number and a `locations` row (§16.1), and `apply_to_ward_series()` returns the
keep-mask plus an exclusion report that logs on every run.

Two traps from the profile: filter waterlogging on **`Sub Category`, not
`Category`** (§10.1 — 84% of it sits under `Road Maintenance(Engg)`), and keep
source strings byte-exact, including the double space in
`Storm  Water Drain(SWD)`.

---

## Queue

**2. `data/reference/hazard_categories.yaml`.** Hand-curated map from exact
source category/sub-category strings to `WATERLOG` / `GARBAGE`, and within
waterlogging to `event` vs `maintenance`. Preserve source strings byte-exactly —
note the double space in `Storm  Water Drain(SWD)`. Record the row count beside
each entry so drift is visible in a diff. This file is a citable methodological
artifact, not a config detail. **Blocks the current task.**

**3. Hotspot register dedup decision.** The three KML layers are already loaded
unmerged (§16.1: 398 points, `hotspot_source` per layer). What remains is the
decision the original item deferred: whether and how to merge them, given they
are near-disjoint (§8.2) and their provenance is still unestablished. The dedup
threshold is a documented decision, not a default.

---

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
