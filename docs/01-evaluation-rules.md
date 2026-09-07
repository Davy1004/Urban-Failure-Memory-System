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

## Outstanding caveat

Every figure above uses the city-wide mean of 9 ERA5 cells applied uniformly to
all 198 wards, because no ward can be assigned a grid cell until the crosswalk
exists. The split is therefore by *day*, not by *place*. Bengaluru's storms are
localised, so these figures understate the true lift. Recompute per-ward after
the crosswalk — this is queue item 2 in `NEXT.md`.
