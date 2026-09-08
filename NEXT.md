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

## Current task — hazard categories YAML, then the complaints loader

**Analysis is closed.** Build from here.

**First: `data/reference/hazard_categories.yaml`.** Hand-curated map from exact
source category and sub-category strings to `WATERLOG` / `GARBAGE`, and within
waterlogging to `event` vs `maintenance`. Preserve source strings byte-exactly -
note the double space in `Storm  Water Drain(SWD)`. Record the row count beside
each entry so vocabulary drift shows in a diff. Profile §10.1 has the counts,
§12.4 the event/maintenance evidence.

Give it a **work-order section too**, replacing the keyword regex used for
drainage classification in §25-§26. Same discipline: exact strings, counts.

**Then: `app/ingestion/bbmp_complaints.py`.** Idempotent on `Complaint ID`
(globally unique across all six files). Truncates timestamps to DATE
deliberately - the source lost its AM/PM marker, so any time-of-day value would
be fiction. Applies the ward crosswalk, keeps `in_flood_register=false` wards in
the panel, and logs excluded counts unconditionally. Expect ~237k rows.

Everything it needs exists: all 198 ward names resolve to a ward number and a
`locations` row, `apply_to_ward_series()` returns the keep-mask and report, and
`upsert_chunk` handles idempotency.

---

## Design note for Phase 4 — what the dashboard should now show

The original plan built a triage dashboard. Triage is now proven near-
unimprovable, so building a screen that implies otherwise would contradict the
project's own findings. The system should **demonstrate what the analysis
found**, which is a coherent and more honest product:

1. **Standing priority list** — the static top-20. Still worth 14% against 4.7%
   random. Present it as a stable watchlist, not a nightly prediction, and show
   the ceiling beside it.
2. **Relative flooding index per ward, over time** — the quantity that actually
   works. This is the map and the trend chart, and it is the core screen.
3. **Emerging watch** — the rank-based detector, labelled honestly as
   *chronically above norm* rather than *accelerating*, since that is what §2
   established it detects.
4. **Intervention effectiveness** — spend versus change in relative index. This
   is the positive result and the most demonstrable thing in the project. Show
   the quintile bars **with confidence intervals**: §26 established the apparent
   Q5 tail is not real (only the lowest-spend quintile differs from zero;
   quadratic F = 1.26, p = 0.265), so a chart implying a U-shape would misstate
   our own finding. Note that the raw scatter looks weak — the effect is
   conditional on controlling for mean reversion.

Four screens, each backed by a measured result. That is a better mid-review demo
than a triage screen making a claim the data refuses.

---

## Queue

**1. Hotspot register dedup decision.** Three KML layers loaded unmerged (398
points, `hotspot_source` per layer). Establish what each represents before
choosing a threshold.

**2. Housekeeping bundle.** Restate the §12-§14 headlines on IFS so the profile
stops quoting two weather sources. Baseline Alembic against an empty database,
hand-add the three views with `op.execute`, verify against `ufms_schema.sql`,
stamp dev, then add `weather_cells.model` as the first real migration.

**3. Memory engine and the model ladder M0-M3** - to demonstrate the bound, not
to beat it. Report within-night AUC or precision@k, never a pooled AUC.

**4. Frontend (Phase 4)** - the four screens in the design note above.

**5. Re-run §25-§26 drainage classification off the YAML** instead of keywords,
once the YAML exists. Expect the coefficient to move slightly; if it moves a
lot, the keyword match was doing more work than assumed and that is worth
knowing.

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
