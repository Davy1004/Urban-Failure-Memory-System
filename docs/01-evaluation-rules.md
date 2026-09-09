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

## Proof One (restated) — the predictability ceiling

**This replaces the original Proof One. Settled 8 Sep 2026; the superseded text
is kept below the fold.**

> The original claim — that a nightly ranking would reorder meaningfully with
> weather and beat a static list — is **tested and rejected**. A ward-level
> ranking fitted with perfect foresight reaches 15.66% against the honest
> static 14.08%, so at most 1.58 of 23.64 points of headroom is reachable by
> any ward-level score whatsoever. What replaces it is a measurement: *we
> establish the predictability ceiling of complaint-derived urban failure
> triage and locate where it binds.* The event set genuinely moves
> (consecutive-night correlation 0.090), so the static list is not capturing a
> stable phenomenon — and yet nothing observable predicts the movement. That
> conjunction is the finding.

What this means in practice:

- **Do not promise to beat the static baseline.** Report M0–M3 all landing near
  14% against a 37.72% ceiling; the ablation is the evidence.
- **The deliverable is the bound, not the model.** "We measured how much a
  nightly triage list can be improved, and it is 1.6 of 23.6 points."
- **Two supporting results carry it.** The pooled-AUC trap (§19.4) explains why
  others have not noticed, and the agency-register check (profile §21) shows
  the label is finding real places, so the ceiling is not an artefact of a
  broken target.

### Superseded: Proof One as originally written

*If tonight's top 20 is the same 20 every night, this is a report, not a tool.*

- Baseline: static "20 historically worst" list — what an officer uses today.
- Measure precision@20 across held-out rain events.
- Measure Kendall's tau between consecutive events' rankings. Low correlation
  **plus** high precision means the model is reading the weather, not
  memorising the register.
- **Due Phase 3, before the mid-review**, so there is time to adapt if it fails.

## Proof Two — alive, but it can name one ward (profile §22–§23)

**Measured 8 Sep 2026, then corrected the same day. Read both parts.**

**The null matters more than the normalisation.** §22 tested each ward's
normalised-share slope against **zero** and found 0 rising / 10 declining. That
was wrong: the citywide share fell 22% over the window, so a ward declining 5%
is diverging *upward* and was scored as declining.

Against the correct null — a standardised incidence ratio benchmarking each
ward-quarter to the citywide mix, `events / (complaints × city_share)` — the
same data gives **9 rising / 4 declining**.

| Test | Rising | Declining |
|---|---:|---:|
| Raw event count | 7 | 3 |
| Normalised share, null = zero | **0** | 10 |
| **Normalised share, null = city trend** | **9** | 4 |

**Two things are true at once, and both must be reported.**

*The aggregate signal is real.* A permutation null that shuffles each ward's
quarters in time gives a mean of 2.4 rising wards (sd 1.6, max 9 over 2,000
draws) against 9 observed — **permutation p = 0.0010**.

*But almost nothing is individually nameable.* Benjamini–Hochberg FDR over all
103 eligible wards leaves **zero** survivors at q = 0.05, 0.10 or 0.20.
Restricting to the **pre-specified** emerging pool — the 42 eligible wards off
BBMP's register, per §12.5 — leaves exactly **one: Jakkur** (q ≤ 0.10). Declare
that restriction as pre-specified or it is fishing.

**On persistence, the instrument was wrong (corrected 8 Sep, profile §25.1).**
Slope correlation across halves (ρ = 0.035) is not the right test: a ward that
deteriorates and then stays bad has a positive first-half slope and a flat
second-half slope, so real emergence produces low slope correlation by
construction.

Test **level** persistence. Wards in the top 10 by first-half slope end the
second half at mean relative index **1.77**, against 1.45 for wards flagged by
first-half *level* and 1.16 for all eligible wards — **10 of 10 finished above
the city norm**, and the gap versus other wards is **p = 0.0001**. Slope and
level are nearly independent (ρ = 0.132), and slope still enters an OLS of
second-half level at p = 0.051 after controlling for level.

**The claim rests on level persistence and it holds.** But flagged wards do not
significantly exceed their own first-half level (p = 0.23), so the detector
finds *chronically above norm*, not *accelerating*. Say that, not more.

**Rules that follow:**

- **Never test a ward trend against zero.** Benchmark to the city, always. This
  is the same difference-in-differences framing as intervention effectiveness.
- **Report the permutation test alongside per-ward p-values.** "More wards rise
  than chance allows" is defensible; "these nine wards are rising" is not.
- **Never report a share decline as improvement without checking absolute
  counts.** Of the ten zero-null "decliners", four had absolute events *rise*
  (Hoodi 25→32, Horamavu 43→46, Varthur 15→27, Vishwanathnagenahalli 7→8) —
  pure denominator growth. Of the four correct-null decliners, all four fell
  absolutely while the city rose 78%; improvement is on the table only for those.
- Normalisation is still mandatory, and the denominator barely matters
  (all complaints / stable categories / solid-waste agree at ρ = 0.85–0.995).

**Superseded framing (kept because the reasoning is still instructive):**

Complaint volume doubled 2021→2024 and ward growth is **not** uniform
(p10 1.42×, p50 2.00×, p90 3.00×, range 0.87×–4.81×). A trend test on raw
complaint counts finds app adoption, not hazard:

| Series (Theil–Sen + Mann-Kendall, 20 quarters, 103 eligible wards) | Rising | Declining |
|---|---:|---:|
| **Raw event count** | **7** | 3 |
| **Normalised by the ward's own complaint volume** | **0** | 10 |

**Normalisation is mandatory.** Divide by the ward's own total complaints per
period. The denominator choice barely matters — all complaints, categories
present in every year, and solid-waste-only agree at ρ = 0.85–0.995, and all
three give zero rising wards.

**And after normalising there is no emerging signal at ward level.** Zero wards
rise at p < 0.10; the closest is p = 0.139. The test has power — it finds ten
significant declines. The likely cause is granularity: a ward is 3.7 km² and
thousands of complaints a year, while an emerging hotspot is a junction. The
complaint data has no sub-ward geography (§8), so location-level detection is
not possible with this source.

**Do not report Bellandur or Varthur as emerging.** They sit in the raw top 11
purely on volume growth; their share of flooding complaints is not rising. Nor
Hoodi, which is significantly *declining* in share (p = 0.007) despite 3.06×
volume growth.

**Distinguish two claims that §21 ran together.** "Absent from the register with
high total events" means *the register is out of date*. "Rising share" means
*getting worse*. Different tests; for Hoodi, Someshwara, Jakkur and Basavanapura
only the first is supported.

See profile §22.6 for the three options on what Proof Two becomes.

### Superseded: Proof Two as originally written

- Mann-Kendall / CUSUM on per-location complaint rate normalised by rainfall.
- Validate: train through year *n*, check flagged sites show sustained
  elevation in *n+1*.
- Delhi upside if the RTI lands: predict which sites PWD *adds* to next year's
  list, using the municipality's own revisions as ground truth.

## Reporting bias — measured, and it is not socially patterned

Ward-level complaint growth 2021→2024 was tested against every proxy available
(profile §22.2). **The marginalisation proxy shows nothing**: SC+ST population
share, ρ = −0.057, p = 0.42. Population ρ = −0.109, density ρ = 0.014, area
ρ = −0.021, all n.s. By zone, periphery 1.96× vs core 2.01× (p = 0.708).

Two weak real effects: flatter wards grew faster (elevation range ρ = −0.231,
p = 0.001), and already-loud wards grew less (complaints per 1,000 residents
ρ = −0.147, p = 0.039 — saturation).

**So reporting growth is idiosyncratic, not an equity gradient.** That is worth
stating in the paper: it makes the confound a noise problem rather than a bias
problem, and it means correcting for it does not itself introduce social bias.
It does **not** weaken the cross-sectional reporting-propensity concern below —
only the claim about *growth*.

`data/reference/ward_socioeconomic.csv` carries population, SC/ST counts,
density and area per ward, from the BBMP 2014 delimitation file.

### The original cross-sectional concern, unchanged

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

# Measured baselines

**Restated on the ECMWF-IFS basis, 9 Sep 2026.** Everything below is computed
from the real data, not assumed. Train through 2023-12-31, test on the held-out
rain days of 2024-25, ward level, strict event label, city-mean rainfall.

Two bases exist because the rainfall series was upgraded mid-project (§17): a
rain day is a day whose city-mean daily rainfall clears 2.5 mm, and ERA5 and
IFS disagree about which days those are — 138 days against 136. Every figure in
a triple has to come from the same basis or the comparison is meaningless.

**Quote the IFS triple. It is what `weather_cells` defaults to, what the
database holds, and what `/api/v1/watchlist` serves.**

| Benchmark | precision@20 | % of ceiling |
|---|---:|---:|
| **Random 20 wards** | **4.79%** | 12.7% |
| Weather only — IFS, 14 cells | 5.63% | 14.9% |
| **Static "20 historically worst"** | **14.08%** | **37.3%** |
| **Oracle ceiling** | **37.72%** | 100% |

136 held-out rain days, 1,289 strict events. The random floor is a closed form,
not an estimate: k wards drawn without replacement from n catch `k × events/n`,
so per-night precision is `events/n` exactly and independent of k. Profile
§17.4's **4.80%** is a simulated estimate of the same quantity; the two agree to
simulation noise, and 4.79% is the figure to publish.

### The earlier ERA5 basis, kept for reference

138 held-out rain days. Superseded, and quoted only where a §14 figure is being
cited directly.

| Benchmark | precision@20 |
|---|---|
| Random 20 wards | 4.72% |
| Static "20 historically worst" | 13.55% |
| Same list re-ranked daily on all prior history | 13.70% |
| Oracle ceiling | 37.36% |

**The conclusions are unchanged between the two bases.** The static list scores
36.3% of ceiling under ERA5 and 37.3% under IFS; memory beats weather by roughly
threefold either way; the headroom argument (§19) was computed on IFS. Tripling
the grid resolution moved no figure that changes a claim (χ², p = 0.877).

**Never mix them.** 14.08% with 37.72% and 4.79% is one basis; 13.55% with
37.36% and 4.72% is the other. A ceiling from one and a floor from the other
puts a number on a scale it was not measured against.

## Rule: never report precision@k bare

A median rain day carries only 6 strict events citywide and just 14 of 138 test
days have 20 or more, so 20 slots cannot all be right and a perfect oracle still
scores under 50%. **Report the achieved figure, the static baseline, and the
oracle ceiling together, every time.** A precision@20 of 22% reads as failure
alone; against a 37.72% ceiling it is 58% of achievable.

## Rule: stratify by rainfall band

The static baseline itself moves from 8.9% on 2.5–5 mm days to 33.3% on
25 mm-plus days. That spread is larger than any plausible modelling gain, so a
wetter test period flatters a model that is not actually better. Precision@20
must be reported **within rainfall bands**, not pooled.

## Rule: judge Kendall's tau as a pair, never alone

Day-to-day tau measures how much a model reorders; it is not a score on its own.

- Low tau, flat precision → noise.
- High tau, flat precision → the static list wearing a model.
- Low tau, precision above 14.08% → genuine weather response. This is the target.

Separately, tau between the two halves of the period is **0.59** (top-20 overlap
15/20). That is multi-year drift in the underlying ranking, a different quantity
from day-to-day reordering — do not conflate them. It is also evidence for Proof
Two: five wards changed between halves, so the danger set genuinely moves.

## Where the headroom is, and is not

Re-ranking on more history added nothing (13.70 vs 13.55, ERA5 basis).
**Count-based memory
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

### The headroom was measured, and it is not reachable (8 Sep 2026)

**This supersedes the feature plan below.** Profile §19 tested it rather than
assuming it. A ward-level ranking fitted with perfect foresight — cheating,
using the test period's own outcomes — reaches **15.66%** against the honest
**14.08%**.

| | Points | Share of headroom |
|---|---:|---:|
| Headroom, 14.08% to the 37.72% ceiling | 23.64 | 100% |
| **Reachable by any perfect ward-level ranking** | **1.58** | **6.7%** |
| **Irreducibly within-ward / temporal** | **22.06** | **93.3%** |

Consecutive rain nights' event vectors correlate at **0.090**. Which wards
flood tonight is close to independent of which flooded last time, and no ward
attribute predicts the movement.

**The two interaction features named below were built and tested. Both are
worse than memory alone:**

| Model | Within-night AUC | precision@20 |
|---|---:|---:|
| **prior event count alone** | **0.7371** | **14.08%** |
| `conditional_rate_at_current_band` | 0.7091 | 12.94% |
| + `excess_over_city` | 0.6979 | 12.79% |
| memory + interaction + terrain | 0.7332 | 13.82% |

`cond_rate` correlates with plain prior count at r = 0.853 and `excess` at
r = 0.877 — conditioning a thin per-ward history on six rainfall bands adds
more estimation noise than interaction signal. Terrain (elevation, elevation
range, centroid-below-boundary) adds nothing either.

**Do not build the FMI expecting a precision win.** Build the ladder to
demonstrate the bound: M0–M3 all landing near 14% against a 37.7% ceiling *is*
the result, and the ablation is what makes it credible.

### Rule: never report a pooled AUC as evidence a triage model works

A logistic model over all features reaches pooled ROC-AUC **0.749** and looks
successful. Its within-night AUC is 0.737 — and prior count alone also gives
0.737. Rainfall features carry 74–100% of their variance *between* nights,
while precision@k only ever compares wards *within* one night. A night-level
model scores pooled AUC 0.61, within-night AUC exactly **0.500**, and
precision@20 of 4.71% — chance.

**Report within-night AUC, or precision@k, or both. Never a pooled AUC alone.**

### The original feature plan — ASSERTED, THEN MEASURED, AND WRONG

**This section used to state as fact that the headroom would come from memory
interacting with weather. That was an assertion, it was tested, and it is
false.** The features below were the right ones to try and they were tried;
every one scores worse than plain prior event count. `cond_rate` correlates
with `prior_n` at r = 0.853, because a conditional rate estimated from a thin
per-ward history is mostly a noisier restatement of the base rate.

Kept in full so the negative result reads as a decision rather than an
omission — and as a standing reminder that a plausible feature story in this
file is a hypothesis until someone measures it.

The headroom from 13.55% to 37.36% was expected to come from **memory
interacting with weather**, so the FMI was to lead with:

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

---

# Settled decisions (8 Sep 2026)

## The label ceiling — say it out loud

A complaint is a citizen report, not an observed flood, so an unknown share of
the 22 irreducible points in §19.6 is reporting behaviour rather than hydrology.
The two cannot be separated with this data. **The limitations section must say
so** rather than let a reader assume the residual is physical.

The available partial bound, from profile §21: the frozen top-20 is
significantly enriched for wards on BBMP's own agency-observed flood register —
**16 of 20 against a 52% base rate, hypergeometric p = 0.006** — but agrees only
moderately on severity (**Spearman ρ = 0.334**, top-20 overlap 9/20). Reading:
the label finds real places; its error is concentrated in timing and degree, not
in place. That is consistent with the §19.6 decomposition and is the sentence to
put in the paper.

## Location-level triage — expectation recorded, not tested

Everything is ward-level. Per-location the panel is sparser and the base rate
lower, so the §19 conclusion should hold *more* strongly, not less. **This is
untested and recorded as an expectation.** The complaint-to-location join does
not exist and will not be built: §19.6 caps any ward-level gain at 1.58 points,
and a finer unit does not lift that cap.

## Terrain — do not populate for triage

`ward_elevation.csv` is kept: it was cheap, it ranks the right places
qualitatively (the most bowl-like wards are Shettyhalli, Horamavu, Ullalu,
Bagalagunte, Bellandur), and the Learn outputs may want it. But elevation
contributes nothing once memory is in the model, and §19.6 makes further terrain
work unpayable for triage. **Do not chase `imperviousness` or
`drain_distance_m`** for this purpose.

## The pooled-AUC trap is a paper contribution, not just a rule

§19.4 belongs in the paper as a methodological finding in its own right, not
only in this file. A held-out ROC-AUC of 0.749 coexisting with a precision@20
effect of +0.18 points (p = 0.84) is exactly the result that gets published
elsewhere as a working model. The clean explanation is the variance
decomposition: every ward-varying feature has **0%** between-night variance
while rainfall carries 74–100% of its variance between nights, and precision@k
only ever compares wards within one night. Anyone building a location-day triage
model can be fooled the same way.

## Magnitude is a secondary output, not a headline

Profile §20. Weather cannot predict the raw count of failing wards (R² = −0.03;
reporting drift dominates). Against a trailing baseline it reaches R² = 0.196
and 3-class accuracy 50.0% vs a 39.6% majority. The pre-set bar (R² > 0.4, or
3-class meaningfully above majority) is **missed on the first and marginal on
the second**.

Report it as advisory only: the binary "is tonight in the worst third" question
reaches AUC 0.749, and 9 of the 10 most confidently flagged nights were
genuinely severe — but the middle of the distribution is near chance. **Quote
the extremes, never a headline R².**

## Intervention effectiveness — outcome claim RETRACTED (profile §27)

**There is no dose-response.** The published estimate (−0.0240 on log spend,
p = 0.0138, n = 110) does not survive refitting on treated wards only:

| | n | Coefficient | p |
|---|---:|---:|---:|
| All wards (published) | 110 | −0.0240 | 0.0138 |
| **Treated wards only** | **103** | **−0.0064** | **0.833** |
| Treated **indicator**, no dose | 110 | −0.4497 | 0.0084 |

`log1p(spend)` placed 7 untreated wards at 0 while every treated ward clusters
near 16–20, so the slope was fitted through two clusters across a 16-unit gap.
It is a treated-versus-control contrast, and §25.2 had already established that
those 7 wards are not a valid control — they are untreated because BBMP judged
they needed nothing. Their own deltas run from −1.55 to +1.49 with a mean CI of
[−0.778, +1.280].

### Rule: check that the treatment varies before fitting anything to it

**Added 8 Sep 2026, profile §28.** Before a within-unit / fixed-effects design,
report three things and stop if they fail:

1. the distribution of each unit's **first** treatment period — not its modal
   or largest one, because a before/after design needs the moment the unit
   *switches*;
2. how many distinct treatment periods carry a real cohort, **against the
   number of periods available** (this project's window was 8 quarters long, so
   "8 distinct quarters" was the ceiling, not a comfortable pass mark);
3. how many units have enough outcome periods on each side of their own date.

And two questions the three diagnostics do not ask, both of which killed this
design on their own:

- **Is the first treatment inside your window actually the unit's first
  treatment?** Widen to the full history before believing a cohort. Here, 118
  of 181 wards appeared to start in 2021Q1; across all 17,418 dated drainage
  works, **zero** wards had a first-ever treatment inside the window. The
  pile-up was the window edge.
- **Does the "post" period contain observation of the treatment, or does your
  treatment data just stop?** The work orders end 2023Q1 and the outcome panel
  runs to 2025Q1, so 40% of the post period was censoring.

A unit that is always treated has no before. That is not weak identification;
it is no identification.

### Rule: refit any dose-response on treated units only, before reporting it

If the coefficient does not survive dropping the zero-dose group, it is a
treated-versus-control contrast wearing a dose-response's clothes. Report it as
the former, and argue the control group's validity explicitly.

Neither the coefficient, its CI, the residualisation check nor the quintile
table caught this. **The added-variable plot did, immediately** — residualise
both outcome and dose on the controls and scatter the residuals; leverage is the
first thing visible. Use it as the standard figure for any regression this
project reports.

### What survives from §25

The **allocation** findings are about how spend is distributed, not about
outcomes, and are untouched:

**The reverse-causality confound is measurably absent.** Correlation between the pre-period relative index and log spend is
**r = −0.083, p = 0.39**. Spend tracks **ward area** (ρ = +0.474) and raw event
counts (ρ = +0.355), but not relative flooding need. Residualising spend on the
pre-period index therefore changes the coefficient not at all.

**Rules retained for the allocation findings and for any future outcome model:**

1. **Publish the quintile table WITH its confidence intervals — the apparent
   reversal is not real** (corrected 8 Sep, profile §26). Only Q1 differs from
   zero (+0.232, p = 0.022); Q5 is +0.105 with CI [−0.142, +0.353], p = 0.385.
   A quadratic term in log spend is not significant (F = 1.26, p = 0.265), so
   **there is no statistical evidence of non-monotonicity.** Both explanations
   were tested and rejected: Q5 wards are not faster-growing (median volume
   growth 1.98× vs Q1's 1.94×; adding log growth moves the coefficient from
   −0.0240 to −0.0247), and there is no disruption-then-recovery (Q5 2024–25 vs
   2023 = −0.030, p = 0.834). The quintile means are a noisy discretisation;
   the linear estimate on all 110 wards is the reliable one.
2. **Do not claim causality.** Spend is discretionary, not randomised. Absence
   of correlation with the relative index does not exclude selection on
   something unobserved.
   **And state the deflation:** the effect is significant *conditional on the
   controls*, not as a raw association — Spearman(spend, Δ) is −0.163 (p = 0.099)
   among treated wards. The main specification reaches p = 0.014 by controlling
   for the pre-period index, which carries strong mean reversion (−0.788).
   Correct, but it means the relationship is not visible in a raw scatter.
3. **Treated-versus-control is unavailable** — and worse than §25 thought.
   Not only were 103 of 110 eligible wards treated inside the window, but
   5 of the 7 that were not had ₹37–121 M of drainage work *before* it
   (§28.5). "Untreated" meant "no work order ending inside an arbitrary
   24-month box". **The treated indicator (−0.4497, p = 0.0084) is
   therefore not a fallback estimate and must not be reported as one.**
   **Effectiveness is closed: there is no outcome design left** (§28).

**The targeting objection is answered, not deflected** (profile §26.5). Spend
correlates with absolute complaint counts at ρ = +0.274, but **controlling for
ward area that collapses to ρ = −0.050, p = 0.603.** Area fully explains it
(spend vs area +0.474; events vs area +0.649). State it in this order:

> Drainage spend tracks ward area. It correlates with absolute complaint counts
> because large wards generate more complaints of every kind — controlling for
> area, that correlation vanishes. Benchmarked against each ward's own complaint
> mix, allocation is uncorrelated with need (ρ = +0.051, p = 0.60).

**Retracted:** §24's observation that register-absent wards receive more
drainage spend. Tested across all 198 wards it fails — median ₹16.6 M off the
register vs ₹17.3 M on it, Mann-Whitney p = 0.789; 9 of the top 20 spenders are
off the register against a 48% base rate, hypergeometric p = 0.713. It was a
four-ward coincidence. The surviving version is that spend tracks ward size
rather than relative flooding need.
