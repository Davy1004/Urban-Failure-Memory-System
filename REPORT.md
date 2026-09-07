# REPORT — can we predict the size of the night?

Task: NEXT.md "can we predict the size of the night?", plus the six answers to
the previous report's §5. Completed 2026-09-08. Written for the reader who
decides what happens next; assumes no access to the conversation.

**Answer, against the bar you set in advance: the first criterion is missed
decisively, the second is marginal. R² on the target as specified is −0.03.
On a detrended target it is 0.196 (95% CI 0.082–0.278), and 3-class accuracy is
50.0% against a 39.6% majority — +10.5 points, but the CI on that gap includes
zero.**

**The defensible claim is narrow: weather reliably flags the handful of worst
nights and is near-chance in the middle. Nine of the ten nights it was most
confident about were genuinely severe.** I would report this as an advisory
secondary output and not promote it further.

Full write-up: profile §20 (magnitude) and §21 (label ceiling). Evaluation
rules updated with Proof One restated and five settled decisions recorded.

---

## 1. The specified target fails, and the reason is not weather

The brief named the target as "the count of distinct wards with a strict event,
per rain day". That target is not stationary:

| Year | Rain days | Mean events/rain day | Total complaints |
|---|---:|---:|---:|
| 2020 | 121 | 3.99 | 91,620 |
| 2021 | 126 | 3.90 | 103,504 |
| 2022 | 114 | 6.94 | 118,394 |
| 2023 | 86 | 4.33 | 119,140 |
| 2024 | 107 | 7.84 | 207,016 |
| 2025 | 29 | 15.52 | 126,974 |

Train mean 4.78, test mean 9.48. Correlation with time 0.243; with city
rainfall 0.214. **The reporting trend is as strong as the weather signal.**

| Model | R² | MAE |
|---|---:|---:|
| Mean baseline (train mean) | −0.136 | 6.65 |
| Rainfall-threshold baseline (4 buckets) | −0.065 | 6.48 |
| **Linear regression, weather only** | **−0.032** | 6.31 |
| Poisson GLM, weather only | −0.033 | 6.30 |
| Linear + explicit time trend | 0.090 | 6.28 |
| Time trend alone, no weather | −0.055 | 6.64 |

Every R² is at or below zero. Weather models beat the mean baseline but all are
worse than predicting the test mean.

## 2. What I changed, and why — flagging this as a deviation

I re-ran against a **detrended target**: events divided by the trailing 90-day
mean events per rain day, computed from prior days only so no model sees the
future trend.

This is a change to the specified target and you should weigh it as one. My
reasoning: the absolute target is dominated by BBMP's reporting-channel growth
(§9.7), so measuring it answers "did complaint volume grow" rather than "does
weather predict severity". The relative question is also the one an operations
desk actually asks. But it is a weaker operational claim than the absolute one
would have been, and it requires maintaining a trailing baseline in production
that drifts with reporting channels rather than weather.

## 3. Results on the fair target

| Model | R² | MAE |
|---|---:|---:|
| Mean baseline | −0.007 | 0.880 |
| **Linear regression, weather only** | **0.196** | **0.788** |

Bootstrap, 1,000 resamples of test nights: R² **0.187, 95% CI [0.082, 0.278]**.
Excludes zero; excludes 0.4.

Single-feature models, since the multivariate coefficients are badly collinear
(rain_max_cell +0.809 against city_rain −0.645):

| Feature(s) | R² | Binary AUC | 3-class acc |
|---|---:|---:|---:|
| city rainfall alone | 0.123 | 0.715 | **51.5%** |
| max-cell rainfall alone | 0.137 | 0.735 | 50.0% |
| rain percentile alone | 0.122 | 0.710 | 47.0% |
| antecedent 7d alone | 0.095 | 0.610 | 41.7% |
| spread (max cell − city mean) | 0.075 | 0.706 | 47.7% |
| all six | **0.196** | **0.749** | 50.0% |

Most of the signal is simply how much rain fell. The six-feature model doubles
R² over city rainfall alone and does not improve classification at all.

### Operational version

Terciles of the **training** ratio distribution. Test: quiet 48, moderate 49,
severe 35. Majority baseline **39.6%** (bootstrap).

3-class classifier, **accuracy 50.0%**:

| true \ predicted | quiet | moderate | severe |
|---|---:|---:|---:|
| **quiet** | 32 | 8 | 8 |
| **moderate** | 26 | 12 | 11 |
| **severe** | 8 | 5 | 22 |

Quiet 32/48 and severe 22/35 are called reasonably. The middle collapses — 26 of
49 moderate nights called quiet. **The extremes are separable, the middle is
not.**

Gap over majority: **+10.5 points, 95% CI [−0.8, +20.5]**; the model wins in
96.1% of resamples. Positive, not comfortably significant.

### Where it is genuinely useful

Binary "is tonight in the worst third of recent rain nights", base rate 26.5%:
**ROC-AUC 0.749 (CI 0.650–0.841)**, accuracy 79.3% vs 73.5% majority.

| Flagged | Genuinely severe | Precision |
|---|---|---:|
| top 5 | 5/5 | 100% |
| top 10 | 9/10 | **90%** |
| top 15 | 11/15 | 73% |
| top 20 | 11/20 | 55% |
| top 40 | 20/40 | 50% |

Over 18 months, the ten nights the model was most confident about contained
nine genuinely severe ones, against a 26.5% base rate. Small counts at the top —
read with care — but the ordering is monotone and the AUC interval excludes
chance.

## 4. Verdict against your pre-set bar

| Criterion | Result | Met? |
|---|---|---|
| R² > ~0.4 | 0.196, CI [0.082, 0.278] | **No, decisively** |
| 3-class meaningfully above majority | 50.0% vs 39.6%, CI on gap [−0.8, +20.5] | **Marginal** |
| (unplanned) binary AUC | 0.749, CI [0.650, 0.841] | Clearly above chance |

Your rule said above the bar means "a real weather-driven output and the honest
product statement becomes *predictable in magnitude, not in location*"; below
means "weather contributes nothing anywhere".

**Neither branch is quite right, and I am not going to talk it into one.** The
honest position: *unpredictable in location, weakly predictable in magnitude,
and reliable only for the worst nights.* That is a real but secondary output.
It does not rescue triage, and the project still rests mainly on the Learn
outputs — but "weather contributes nothing anywhere" would be too strong, since
an AUC of 0.749 with a CI excluding 0.5 is not nothing.

## 5. The label-ceiling bound (your answer 2)

The frozen top-20 against BBMP's agency-observed register:

| | |
|---|---:|
| Top-20 wards on the register | **16 / 20 (80%)** |
| Register coverage, all 198 wards | 52% |
| Expected under independence | 10.3 / 20 |
| Hypergeometric p | **0.0060** |
| Spearman ρ, events vs register points | **0.334** (p = 1.5e-06) |
| Overlap of the two top-20 lists | 9 / 20 |
| Mean events, register vs non-register wards | 24.7 vs 13.4 (p = 0.0001) |

**The label finds real places.** Four fifths of the wards the complaints rank
worst are independently listed as flood-prone by BBMP — significant enrichment
over the 52% base. But ρ = 0.334 and 9/20 list overlap are not a clean proxy:
the two agree on *which wards are flood-prone* far more than on *how bad each
is*.

Reading: **the label's error is concentrated in timing and degree, not in
place** — which is exactly what §19.6 found independently (place is saturated at
1.58 of 23.64 points; the rest is when). Two separate analyses converging is the
strongest evidence in the report.

A bonus worth noting: the four top-20 wards *not* on the register are Hoodi,
Someshwara, Jakkur and Basavanapura. Under the §12.5 framing those are precisely
the emerging-hotspot candidates — places failing repeatedly that the official
list has not caught up with. Proof Two's population, surfaced unprompted.

## 6. Your other answers — what I did

- **0. Corrected the rules file.** The FMI section no longer reads as a plan
  with a caveat; it is headed "ASSERTED, THEN MEASURED, AND WRONG" and states
  the r = 0.853 explanation. The original text is kept in full so the negative
  result reads as a decision.
- **1. Proof One restated**, in your words, as the live text. The original is
  kept below a "Superseded" heading. Practical consequences spelled out: do not
  promise to beat the static baseline; the deliverable is the bound.
- **2. Label ceiling** — §21 above, plus a standing note in the rules file with
  the sentence to put in the limitations.
- **3. Location-level join** — recorded as an untested expectation in the rules
  file, explicitly not to be built.
- **4. Terrain** — `ward_elevation.csv` kept; a note says do not chase
  `imperviousness` or `drain_distance_m` for triage.
- **5. Pooled-AUC trap** — recorded as a paper contribution in its own right,
  not only a rule, with the variance-decomposition explanation.

## 7. What I want a second opinion on

1. **Whether the detrending is acceptable.** It is the difference between "no
   signal" and "a weak one". I think it is necessary and I have flagged it, but
   an examiner could reasonably say the absolute count is the operational
   quantity and it failed. If you want the headline to be the absolute-target
   failure with the relative result as a footnote, say so — it is a framing
   choice, not a re-analysis.
2. **Whether to build the magnitude output at all.** AUC 0.749 and 9/10 on the
   top flagged nights is product-shaped, but it needs a maintained trailing
   baseline and it only works at the extremes. It is perhaps two days of work.
   My inclination is to build it *after* the Learn outputs, not before.
3. **The housekeeping bundle has fallen off the queue.** The previous round
   agreed two jobs — restate §12–§14 headlines on IFS, and baseline Alembic then
   add `weather_cells.model`. Neither is in the current NEXT.md. The IFS one
   matters: the profile now quotes ERA5 figures in §12–§14 and IFS figures in
   §17–§21, so the inconsistency you wanted closed is now *internal to the
   document*. I did not do it unasked because the current task was explicitly
   one session's work, but it should go back on the queue.
4. **Whether §20 belongs in the paper at all.** A marginal magnitude result may
   dilute a clean negative headline. It could equally strengthen it — "we
   checked whether weather helps anywhere, and here is the one place it
   slightly does". Your call on the narrative.

## 8. Verification

57 tests pass (unchanged — this task added analysis, not pipeline code).
Database unchanged: `locations` 596, `weather_observations` 1,309,896,
`weather_daily` 54,579.

Temporal discipline: models fit on rain days ≤ 2023-12-31, evaluated on the 136
rain days of 2024-01-01 → 2025-06-19. The trailing baseline uses a 90-day window
of strictly prior rain days. Class edges come from the training distribution,
never the test. Bootstrap CIs resample test nights, 1,000 draws.
