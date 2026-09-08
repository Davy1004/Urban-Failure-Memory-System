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

## Current task — intervention effectiveness, first real build

Profile §24 says the work orders are feasible: ~1,350 usable drainage works
across 166 wards, ward/date/cost complete for 183 of 198. This is now the
project's most promising output and the only one with a source independent of
the complaint feed.

**Build the dose-response analysis**, not treated-vs-control — only 32 wards are
untreated and they are not exchangeable.

1. **Recover the 15 dateless wards first** if it is cheap. Wards 184-198 carry a
   legacy schema; dates look regex-recoverable from the concatenated `brnumber`
   string. An hour, and it restores Bilekahalli, Begur, Gottigere and Arakere -
   active flood wards. Timebox it; if the regex is fragile, drop them and say so.
2. **Hand-curate the drainage classification.** Keyword matching gave 36.4% but
   many road works also mention drains. Same discipline as the hazard YAML:
   exact source strings, counts beside each entry, committed as an artifact.
3. **Design it as difference-in-differences on the relative index**, reusing
   §23's `rel(w,q) = events / (complaints x city_share)`. Never test against
   zero. Spend is the dose; the outcome is the change in `rel` after completion
   versus before.
4. **Jakkur is the case study.** Rs 494M of drainage spend and a significantly
   *rising* flooding share. Either the works failed or they were a response to a
   worsening problem - separating those is the whole point.

Watch the obvious confound: **spend is not random.** BBMP spends where it thinks
there is a problem, so naive dose-response will show "more spend, more flooding".
Control for prior level, not just prior trend, and say plainly if the design
cannot separate targeting from effect.

---

## The project-level call — read this one yourself

Both proofs are negative-shaped. That needs saying out loud rather than being
absorbed one report at a time.

**What the project actually has now**, and it is more than it feels like:

- A **measured predictability ceiling** for complaint-derived triage: 1.58 of
  23.64 points reachable by any ward-level score whatsoever.
- The **pooled-AUC trap**, with a clean variance decomposition. Publishable on
  its own; anyone building a location-day triage model can be fooled the same way.
- The **reporting-growth confound**: seven spurious emerging hotspots over five
  years, every one explained by volume growth — including Bellandur and Varthur,
  the two most notorious flooding wards in Bengaluru, appearing as *newly
  emerging*. That example alone is worth the paper.
- **Convergent validity**: two independent methods agreeing that place is
  saturated and the residual is timing.
- A working system, 57 tests, reproducible pipeline.

**The honest thesis has changed** from "we built a predictor" to *"we measured
what civic complaint data can and cannot support for urban failure prediction,
and it is less than the literature assumes."* That is a better paper than a
marginal accuracy win, and every claim in it is defensible line by line because
it was measured rather than asserted.

**The risk is not the science, it is the audience.** A jury expecting a working
predictor may not immediately value a rigorous negative. That is a real risk and
it is Tanmay's to manage, not ours.

**Action for Tanmay, before December:** take this to your guide. Not the numbers
— the framing. "Our results are turning out to be measured limits rather than a
working predictor; is a rigorous negative acceptable for this project, or does
the department expect a positive?" Five minutes, and the answer changes what the
next three months optimise for. Do not discover it at the mid-review.

**Update, 8 Sep 2026 — the framing above softens slightly, but not much.**
Proof Two is no longer purely negative: benchmarked against the city trend there
are 9 upward-diverging wards and a permutation p of 0.0010, plus one nameable
case (Jakkur) validated against its own Rs 494M of drainage spend. And the work
orders are feasible, so intervention effectiveness is a live positive output
rather than a hope.

So the honest thesis is now *"we measured what complaint data can and cannot
support, and here is the narrow band where it can"* rather than a flat negative.
**The conversation with the guide is still worth having** — the headline results
are still limits rather than a working predictor — but you can now go in with
one demonstrated emerging hotspot and a funded-works effectiveness analysis in
progress, which is a materially easier conversation than a pure negative.

---

## Queue

**1. Recover wards 184-198 from the legacy work-order schema** if not done as
part of the current task.

**2. `data/reference/hazard_categories.yaml`.** Hand-curated map from exact
source category and sub-category strings to `WATERLOG` / `GARBAGE`, and within
waterlogging to `event` vs `maintenance`. Preserve source strings byte-exactly.

**3. Complaints loader.** `app/ingestion/bbmp_complaints.py`, driven by that
YAML. Idempotent on `Complaint ID`. Truncates timestamps to DATE. Applies the
crosswalk, keeps `in_flood_register=false` wards, logs excluded counts.

**4. Housekeeping bundle.** Restate the §12-§14 headlines on IFS so the profile
stops quoting two weather sources. Baseline Alembic against an empty database,
hand-add the three views with `op.execute`, verify against `ufms_schema.sql`,
stamp dev, then add `weather_cells.model` as the first real migration.

**5. Decide how Proof Two is presented.** §23 gives an aggregate result
(permutation p = 0.0010) and exactly one nameable ward. REPORT.md §6 recommends
reporting the aggregate as the finding and Jakkur as a worked case.

**6. Hotspot register dedup decision.** Three KML layers loaded unmerged.

**7. Model ladder M0-M3 — to demonstrate the bound, not to beat it.**
Report within-night AUC or precision@k, never a pooled AUC.

**8. Magnitude advisory badge (Phase 4, half a day).**

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
