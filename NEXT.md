# NEXT — the work queue

**How to use this file.** Read it, do the task under "Current task", then move
that block into "Done log" with the date and a one-line result, and promote the
next item from "Queue". If a task's spec turns out to be wrong or impossible,
stop and say so rather than improvising around it.

Standing rules live in `CLAUDE.md` and `docs/01-evaluation-rules.md`. Read both
before starting anything here.

---

## Current task — recompute §13 and §14 per-ward

Everything measured so far used the city-wide mean of 9 ERA5 cells applied
uniformly to all 198 wards, so the split is really by day. With the crosswalk
in place, assign each ward its nearest cell (`Location.cell_id`, haversine is
fine) and rebuild both sections. §12.6 predicts every figure is understated.
Report the before/after side by side.

**Read §15.2 first.** The crosswalk maps only **102 of 198 wards** to a ward
number, covering 59.7% of complaint rows. The register does not list the other
96 wards, so they have no coordinates and cannot be assigned a nearest cell
from this source. Decide explicitly how to handle them before starting —
options are to restrict the per-ward analysis to the 102 mapped wards (and
report it as a subset, not as the panel), or to source ward centroids from the
OpenCity ward-boundary file listed in `docs/00-build-plan.md`. The second is
more work and gives all 198.

---

## Queue

**3. Complaints loader.** `app/ingestion/bbmp_complaints.py`, driven by
`data/reference/hazard_categories.yaml` (see below). Idempotent on
`Complaint ID`. Truncates timestamps to DATE deliberately — the source lost its
AM/PM marker, so any time-of-day value would be fiction. Applies the crosswalk;
logs excluded rows.

**4. `data/reference/hazard_categories.yaml`.** Hand-curated map from exact
source category/sub-category strings to `WATERLOG` / `GARBAGE`, and within
waterlogging to `event` vs `maintenance`. Preserve source strings byte-exactly —
note the double space in `Storm  Water Drain(SWD)`. Record the row count beside
each entry so drift is visible in a diff. This file is a citable methodological
artifact, not a config detail.

**5. Hotspot register loader.** Three KML layers, near-disjoint, ~390 locations.
Load all three into `locations` with `hotspot_source` set per layer. **Do not
merge them** until we understand what each layer represents. Dedup threshold is
a documented decision, not a default.

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
