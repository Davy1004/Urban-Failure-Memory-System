# Evaluation rules

These decide whether the results are valid. Violating any one of them
invalidates the paper, usually invisibly.

## Splits

- **Temporal only.** Train on earlier seasons, test on later ones. Never
  `train_test_split(shuffle=True)`.
- **Block by rainfall event** so a single storm cannot appear in both train
  and test. (Precedent: HESS 28, 5443 (2024) split on events first.)
- **Spatial blocking** for any point-level data — `neighbour_memory` reads
  from adjacent cells, so a random point split leaks across the boundary.

## Metrics

Base rate is ~0.5%. A model predicting "no failure" always scores 99.5%.

- **precision@k** — of the k locations you named, how many failed. The
  headline metric; k = 20 matches real crew capacity.
- **PR-AUC** — not ROC-AUC, which flatters on imbalanced data.
- **Brier score + calibration curve + ECE**.
- **Print the base rate beside every figure.**
- The word "accuracy" does not appear in the report.

## The model ladder

| | Features | Role |
|---|---|---|
| M0 | rainfall threshold rule, no ML | the baseline to beat |
| M1 | weather only | naive version |
| M2 | weather + terrain | does geography alone explain it? |
| M3 | weather + terrain + Failure Memory Index | **the system** |

## Proof One — the ranking is dynamic

*If tonight's top 20 is the same 20 every night, this is a report, not a tool.*

- Baseline: static "20 historically worst" list — what an officer uses today.
- Measure precision@20 across held-out rain events.
- Measure Kendall's tau between consecutive events' rankings. Low correlation
  **plus** high precision means the model is reading the weather, not
  memorising the register.
- **Due Phase 3, before the mid-review**, so there is time to adapt if it fails.

## Proof Two — emerging detection finds real additions

- Mann-Kendall / CUSUM on per-location complaint rate normalised by rainfall.
- Validate: train through year *n*, check flagged sites show sustained
  elevation in *n+1*.
- Delhi upside if the RTI lands: predict which sites PWD *adds* to next year's
  list, using the municipality's own revisions as ground truth.

## Reporting bias

The label is a complaint, not a flood. Complaint propensity tracks income and
civic awareness, so a model can learn *which wards complain* rather than
*which wards flood* and still score well.

1. Add each ward's baseline complaints-per-capita as a control feature.
2. Model excess complaints over that ward's own baseline, not raw counts.
3. Include ward income/literacy from Census and check feature importance —
   measuring the bias is itself a reportable finding.
4. Validate top-ranked sites against the BBMP register, which is
   agency-observed rather than citizen-reported.

Write a limitations paragraph naming this explicitly.

## Cross-city generalization

Out of scope as an experiment in rev 2 — it is a limitations paragraph.

If asked in the viva: *we do not claim the model transfers; we claim the
architecture does.* Published work (HESS 28, 5443, 2024) found spatial pattern
knowledge transfers between cities while magnitude does not, and that a single
rainfall event sufficed to adapt. Normalising every physical feature to its
local distribution (percentile, return period) is what makes the features
city-invariant; the memory values themselves are recomputed per city.

---

# Measured baselines (2026-09-07)

Everything below is computed from the real data, not assumed. Train through
2023-12-31, test on the 138 rain days of 2024–25, ward level, strict event
label, city-wide mean rainfall.

| Benchmark | precision@20 |
|---|---|
| Random 20 wards | 4.72% |
| **Static "20 historically worst"** | **13.55%** ← the number to beat |
| Same list re-ranked daily on all prior history | 13.70% |
| **Oracle ceiling** | **37.36%** |

## Rule: never report precision@k bare

A median rain day carries only 6 strict events citywide and just 14 of 138 test
days have 20 or more, so 20 slots cannot all be right and a perfect oracle still
scores under 50%. **Report the achieved figure, the static baseline, and the
oracle ceiling together, every time.** A precision@20 of 22% reads as failure
alone; against a 37.36% ceiling it is 59% of achievable.

## Rule: stratify by rainfall band

The static baseline itself moves from 8.9% on 2.5–5 mm days to 33.3% on
25 mm-plus days. That spread is larger than any plausible modelling gain, so a
wetter test period flatters a model that is not actually better. Precision@20
must be reported **within rainfall bands**, not pooled.

## Rule: judge Kendall's tau as a pair, never alone

Day-to-day tau measures how much a model reorders; it is not a score on its own.

- Low tau, flat precision → noise.
- High tau, flat precision → the static list wearing a model.
- Low tau, precision above 13.55% → genuine weather response. This is the target.

Separately, tau between the two halves of the period is **0.59** (top-20 overlap
15/20). That is multi-year drift in the underlying ranking, a different quantity
from day-to-day reordering — do not conflate them. It is also evidence for Proof
Two: five wards changed between halves, so the danger set genuinely moves.

## Where the headroom is, and is not

Re-ranking on more history added nothing (13.70 vs 13.55). **Count-based memory
features are saturated** — `recurrence_count`, `recurrence_rate` and
`recurrence_percentile` reproduce the static list and little else. If the
Failure Memory Index is built mostly from those, M3 will not beat M2.

### Weather alone ranks at chance — measured

Ranking all 198 wards by their own cell's daily rainfall, ties broken randomly,
on the same held-out rain days (profile §17.4):

| Ranker | precision@20 | % of ceiling |
|---|---:|---:|
| Weather only — ERA5, 3 cells over the city | 6.46% | 17.1% |
| Weather only — ECMWF-IFS, 14 cells | **5.63%** | 14.9% |
| **Random ward order** | **4.80%** | 12.7% |
| **Memory only — static top-20** | **14.08%** | 37.3% |
| Oracle ceiling | 37.72% | 100% |

**M1 is structurally close to degenerate for triage.** A weather-only ranker
sees about 4.8 distinct rainfall values across 198 wards under ERA5 and 12.9
under IFS, so roughly 14 wards share every value and within-cell order is
arbitrary. It is not a weak baseline that better tuning improves; it is a
ranker with almost no per-ward information to rank on.

Tripling the grid resolution made it *worse*, not better (6.46% → 5.63%),
because the finer grid breaks up whatever accidental blocking the coarse cells
provided. Both sit at chance.

**Report this as a finding, and expect to state it in the paper.** It is the
project's central thesis measured directly rather than asserted: weather alone
cannot solve the spatial problem. This also means M1's expected score is ~5%,
so **do not read a low M1 as a bug** — it is the predicted result, and M2 must
be compared against it knowing that.

The headroom from 13.55% to 37.36% has to come from **memory interacting with
weather**, so the FMI must lead with:

- `rain_sensitivity_mm` — rainfall at which *this ward's* historical failure
  probability crosses 50%. Already in the schema; now known to be the important one.
- `ward_rain_response_slope` — how sharply this ward's failure probability rises
  with rainfall.
- `conditional_rate_at_current_band` — P(failure | this ward, rainfall in
  tonight's decile), prior data only.
- `excess_over_city` — this ward's failure rate at a given rainfall minus the
  citywide rate at that rainfall. Isolates the ward-specific component after
  removing the city-wide rain effect, which is exactly what the static list
  cannot express.

Frequency features stay in as the floor. They are simply not where the gain is.

## Two labels, not one

Complaint streams conflate **event reports** with **maintenance requests**.

| Label | Ward-days | Rate | Lift on rain days |
|---|---|---|---|
| Broad (all waterlogging categories) | 30,993 | 7.99% | 1.44x |
| **Strict (water stagnation and blockage)** | 6,045 | **1.56%** | **3.06x** |

`Road side drains` is 66% of the broad label and lifts only 1.33x — it is a
request to clean a drain, filed on any dry Tuesday, not a report that something
flooded. Training M1–M3 on the merged label asks the model to predict a
maintenance backlog from rainfall, and it will deservedly fail.

Model the two separately: **failure events** (strict) is the prediction target;
**maintenance demand** (broad) is a feature and a second dashboard output.

## Rainfall alignment: same day

Tested. Lag 0 is correct — lag 1 is indistinguishable from noise (chi-squared
p = 0.695) and lags 2 and 3 are monotonically worse, which is what a genuine
same-day signal decaying under mis-alignment looks like. The 3-day maximum
window scores a higher lift (3.43) purely through a falling denominator; it
describes antecedent dryness, already covered by `antecedent_7d_mm`. Align
rainfall to the complaint date.

## Resolved caveat: per-ward rainfall does not change these figures

Earlier versions of this file warned that every figure used a city-wide mean
and therefore understated the true lift. **That has been tested and rejected**
(profile §16 and §17).

The crosswalk now maps all 198 wards to a centroid, and the pipeline runs on
ECMWF-IFS at ~9 km, which resolves BBMP into 14 cells rather than ERA5's 3.
Per-ward rainfall moves the strict lag-0 lift only 3.06 → 3.00 (χ², p = 0.877)
and still costs 6% on precision@20 when used to restrict the candidate pool.

**Quote the city-mean figures without apology.** The one thing still untested is
gauge resolution (~1 km): KSNDMC has 131 gauges inside BBMP, median 0.95 km from
each ward centroid, but only 5 report to the national portal and only from
August 2023 (profile §18). That is an RTI, not a download, and §17.4 above shows
it would sharpen the weather features rather than overturn the conclusion.
