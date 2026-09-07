# REPORT — finer rainfall tested; KSNDMC investigated

Task: NEXT.md "test whether finer rainfall exists", plus the four answers to
the previous report's §8. Completed 2026-09-08. Written for the reader who
decides what happens next; assumes no access to the conversation.

**Headline, in one line: the finer model exists and is 4.7× better resolved,
the backfill was run, and per-ward rainfall still changes nothing (χ²,
p = 0.877). The limit is not rainfall resolution. Weather alone ranks at
chance — 5.63% against a 4.80% random baseline, versus 14.08% for memory
alone.**

---

## 1. Step 1–2: does a finer product exist?

Yes, and better than the task assumed. Rather than fetching a 5×5 grid and
inferring resolution, I asked the archive API to echo the **snapped grid-cell
coordinate** for each of the 198 ward centroids. That measures effective
resolution directly, in three requests per model, with no time series at all.

| Model | Distinct cells over BBMP | Modal cell holds | Native step |
|---|---:|---:|---|
| `era5` | **3** | 79% | 0.25° (27.8 km) |
| `era5_land` | 9 | 35% | 0.10° (11.1 km) |
| `ecmwf_ifs` | **14** | **28%** | 0.070° lat (7.8 km) |

Two corrections to the task's framing:

- **`era5_land` is unusable.** Its grid is fine, but Open-Meteo returns `null`
  for every `precipitation` hour on that model. Verified across several date
  ranges; it returns real values for other variables. Fine grid, no rain data.
- **ERA5 gives the city 3 cells, not the 5 I reported in §16.** Our production
  grid was nine hand-placed 0.2° points, which snapped onto three ERA5 cells.
  The earlier "5 cells, 89% modal" figure described our over-sampled grid, not
  the reanalysis. The true ERA5 picture is worse than reported: 3 cells, 79%.

Wet-month test, 2022-09, all 198 wards:

| | era5 | ecmwf_ifs |
|---|---:|---:|
| Distinct cells | 3 | 14 |
| Modal cell share | 79% | **28%** |
| Mean daily across-ward spread | 1.44 mm | **4.03 mm** |
| Median / max spread | 0.40 / 10.8 | 1.50 / 20.9 |
| Mean across-ward SD | 0.31 | 0.98 |
| Days with a mixed wet/dry verdict | 1 of 30 | **7 of 30** |

## 2. Step 3: the decision, and the backfill

The rule was: stop at 80%+ modal; backfill at ~40% or below with a materially
larger spread. **28% with 2.8× the spread** cleared it, so I backfilled.

797,328 hourly rows across the 14 **native IFS cell centres** (not a grid of my
own — using the model's own centres avoids resampling its grid onto ours),
2019-01-01 → 2025-06-30, aggregated to 54,579 cell-days. All 198 wards
reassigned by haversine. Ward distribution: 56 / 28 / 26 / 26 / 20 / 9 / 8 / 6
/ 5 / 4 / 3 / 3 / 2 / 2.

### §13 recomputed

| Series | ERA5 city-mean | IFS city-mean | IFS per-ward | vs ERA5 |
|---|---:|---:|---:|---:|
| **lag 0** | 3.06 | 3.09 | **3.00** | −2.1% |
| lag 1 | 3.13 | 3.07 | 3.09 | −1.1% |
| lag 2 | 2.74 | 2.69 | 2.59 | −5.3% |
| lag 3 | 2.44 | 2.32 | 2.38 | −2.4% |
| max prior 3 days | 3.43 | 3.45 | 3.40 | −0.8% |

lag 0 per-ward: 3,308 / 111,496 wet (2.9669%) vs 0.9903% dry. **χ² against ERA5
city-mean: p = 0.877.**

### §14 recomputed

| Variant | Days | precision@20 | Ceiling | % of ceiling |
|---|---:|---:|---:|---:|
| (A) ERA5 city-mean rain days | 138 | 13.55% | 37.36% | 36.3% |
| (B) IFS city-mean rain days | 136 | **14.08%** | 37.72% | 37.3% |
| (C) IFS rain days, wet wards only | 136 | 13.24% | 34.34% | 38.5% |

Like-for-like the per-ward restriction costs **−6.0%**, against ERA5's −6.4%.
Identical behaviour.

**Why it does not help at 9 km.** On an IFS city rain day, **180 of 198 wards
are individually wet**, up from 173 under ERA5. The finer grid widened the
candidate pool rather than narrowing it, because IFS is simply wetter
(Sept-2022 median ward total 101.5 mm vs ERA5's 90.6 mm). The grid *does*
differentiate the city far better — mixed wet/dry verdicts on 411 of 1,959 days
(21%) against ERA5's near-zero — but that differentiation does not align with
where complaints appear.

**This converts an untestable hypothesis into a tested and rejected one.** That
was the substance of your answer #2, and it is now resolved in the direction
you suspected was still open.

## 3. The finding I did not expect: weather alone ranks at chance

Your answer #3 predicted M1 would be structurally degenerate. I measured it
rather than asserting it. Ranking all 198 wards by their own cell's daily
rainfall, ties broken randomly, on the same 136 held-out rain days:

| Ranker | precision@20 | % of ceiling |
|---|---:|---:|
| Weather only — ERA5, 3 cells | 6.46% | 17.1% |
| Weather only — IFS, 14 cells | **5.63%** | 14.9% |
| **Random ward order** | **4.80%** | 12.7% |
| **Memory only — static top-20** | **14.08%** | 37.3% |
| Oracle ceiling | 37.72% | 100% |

Your prediction holds, with one twist worth having: **the finer model scores
*lower* (6.46% → 5.63%)**, because IFS spreads wards across 14 cells and breaks
whatever accidental blocking ERA5's three coarse cells gave. Both are at
chance. A ranker sees 4.8 distinct rainfall values across 198 wards under ERA5
and 12.9 under IFS — it is ordering 198 items with about a dozen keys, so ~14
wards share every value and within-cell order is arbitrary.

Written into `docs/01-evaluation-rules.md` under the headroom section, with the
operational consequence stated: **expect M1 ≈ 5%; do not read it as a bug.**

## 4. KSNDMC: locations yes, time series no

**The network is excellent.** From OpenCity, public domain, no credentials:
**131 telemetric rain gauges inside BBMP** (5,929 across Karnataka).

| Nearest gauge per ward centroid | km |
|---|---:|
| min | 0.01 |
| **median** | **0.95** |
| p90 | 1.51 |
| max | 2.46 |

195 of 198 wards within 2 km; **all 198 within 3 km**. One gauge per ~9 km².
A companion CSV lists 198 gauges with commissioning dates from 2013, so the
network predates the complaint window. This would be a different class of
measurement from any reanalysis.

**The time series is not there.** National Water Data Portal,
`rainfall-telemetry-hourly-karnataka-department`. CKAN API open, no
credentials. But:

- The **1991–2020 CSV is 342 bytes** — one data row, dated 2008. Effectively
  empty. The "1991–2030 in segments" listing is misleading.
- The 2021–2025 CSV is 83.5 MB but holds only 683,619 rows for *all* of
  Karnataka, 686 stations, **earliest timestamp 2021-08-08**.
- Bangalore Urban + Rural: **21 stations, data from 2023-07-15**.
- **Inside BBMP: 5 stations, 3,092 rows, from 2023-08-06.**
- Nearest *reporting* station per ward: median **7.13 km**; only 10 of 198
  wards within 2 km — worse in practice than the 9 km IFS grid.
- Hourly completeness ≈1.1% of hours; these look event-triggered, not
  continuous.

So of 131 published gauge locations inside BBMP, five report to the national
portal and only from August 2023 — a ~23-month overlap with a window ending
June 2025, and nothing for 2020–2022.

**Recommendation: stop spending on the NWDP route.** The locations file proves
the observations exist; KSNDMC holds them on its own infrastructure. That is an
RTI or a formal data request to KSNDMC / Karnataka Revenue Department (Disaster
Management), not a download — months-scale, uncertain, and it **must not block
the pipeline**. §17.4 is the reason it is safe not to block: weather alone
ranks at chance, so better rainfall sharpens the weather features rather than
overturning the conclusion that memory carries the ranking.

## 5. Your four answers — what I did

1. **`Subedarapalya` → ward 65: accepted, flag kept.** No change needed; the
   CSV already carries the low-confidence note and the elimination reasoning.
   Did not chase the BBMP PDF.
2. **§12.6 downgraded, then upgraded again.** You asked for "UNTESTABLE AT ERA5
   RESOLUTION — retest if finer rainfall is obtained". Finer rainfall was
   obtained in the same session, so I wrote the end state instead: **"TESTED
   AND REJECTED AT 9 km"**, with the ERA5 run described as demonstrating ERA5's
   limits rather than testing the hypothesis — your framing, kept, as the
   history. The remaining open case is gauge resolution (~1 km), explicitly
   named. If you would rather I had left the intermediate wording in place, it
   is a one-line revert.
3. **§16.6 tightened** to M1 strictly plus M2's weather component, with the
   measured degeneracy in place of the assertion. §16 now carries a
   "superseded in part by §17" banner rather than being rewritten, so the
   reasoning chain stays legible.
4. **Queue: noted.** You had already swapped it; nothing to do. Point taken
   about reordering a clear dependency myself.

## 6. What I want a second opinion on

1. **Whether the IFS switch should have been a switch at all.** I made
   `ecmwf_ifs` the CLI default and repointed all 198 wards at IFS cells, but
   kept the ERA5 data in place (cells 1–9 ERA5, 10–23 IFS, distinguished per
   observation by `weather_observations.source_id`). The published headline
   numbers in §12–§14 are still the ERA5 city-mean ones, because they are
   within noise of the IFS ones and re-numbering everything would churn the
   document for no measured gain. **So the docs quote ERA5 figures while the
   database is now primarily IFS.** That is defensible but it is a seam, and if
   you would rather the headline numbers were restated on IFS (13.55% → 14.08%)
   say so and I will do the pass.
2. **Schema gap: `weather_cells` and `weather_observations` have no `model`
   column.** Provenance currently rides on `source_id` and on which cell ids
   belong to which model, which is implicit and fragile. The clean fix is a
   `model` column on `weather_cells`, but Alembic still has no baseline
   revision (CLAUDE.md), so any schema change means stamping a baseline first.
   Worth doing before the complaints loader adds more volume.
3. **Whether to delete the ERA5 rows.** 512,568 observations and 21,357
   cell-days now serve only as the baseline comparison. Keeping them costs
   ~40 MB and one confusing seam; deleting them loses the reproducible
   before/after. I kept them. Cheap either way, but it should be a decision.
4. **The 2.5 mm threshold under IFS.** IFS is wetter than ERA5, so the same
   threshold now labels 180 of 198 wards wet on a rain day. If per-ward rain
   is ever used as a *filter* rather than a feature, that threshold should be
   recalibrated per model — probably to a percentile rather than an absolute.
   Not urgent while nothing filters on it.

## 7. Things a future reader should not have to rediscover

- **`era5_land` returns NULL precipitation** through Open-Meteo's archive API.
  It looks like a free upgrade and is not.
- **The archive API echoes the snapped grid-cell coordinate**, and accepts
  comma-separated multi-location requests. Together those measure a model's
  effective resolution over an area in a few seconds — much cheaper than
  fetching series and comparing them.
- **NWDP's "1991–2020" Karnataka rainfall CSV is empty** (342 bytes). Do not
  plan around the advertised date range without a HEAD request first.
- IFS grid longitudes are not on a regular lattice (reduced Gaussian grid), so
  the minimum longitude step (0.0112°) is not the resolution; the latitude step
  (0.0703° ≈ 7.8 km) is.

## 8. Verification

```
57 tests pass (11 new in tests/test_open_meteo_models.py)
python -m app.ingestion.cli weather --city Bengaluru --start 2019-01-01 \
       --end 2025-06-30 --model ecmwf_ifs      # 797,328 rows, idempotent
python -m app.ingestion.cli weather-daily --city Bengaluru   # 54,579 rows
python -m app.ingestion.cli status
```

New tests pin the default model, the 14 IFS cell centres, that every ward is
within 10 km of a cell, and — as a regression guard on the finding that
motivated the switch — that no single cell holds more than 40% of wards.

Database: `locations` 596 · `weather_observations` 1,309,896 (512,568 ERA5 +
797,328 IFS) · `weather_daily` 54,579 (21,357 ERA5 + 33,222 IFS, all 23 cells
× 2,373 days).

Docs changed: profile §17 and §18 added; §12.6 rewritten; §16.6 corrected with
a supersession banner; intro updated. `docs/01-evaluation-rules.md` gains the
weather-at-chance table and a resolved-caveat section. `CLAUDE.md` Phase 1
status updated.
