# REPORT — is the headroom real, or is it noise?

Task: NEXT.md "is the headroom real, or is it noise?". Completed 2026-09-08.
Written for the reader who decides what happens next; assumes no access to the
conversation.

**Answer: it is noise, in the specific sense that matters. A ward-level ranking
fitted with perfect foresight — cheating, using the test period's own outcomes
— reaches 15.66% against the honest 14.08%. Only 1.58 of the 23.64 points
(6.7%) of headroom is ward-level at all. The other 93.3% is within-ward
temporal variation, and nothing observable predicts it.**

This is the negative answer the task said would be a good outcome. It arrives
in September rather than March, and it changes what Phase 3 should build.

Full write-up: profile §19. Evaluation rules updated. New section §19.4 names a
methodological trap that would otherwise have cost the project a false positive.

---

## 1. The three things you asked for

### (a) Is anything associated with surprise membership, and how strongly?

Weakly, and almost entirely at the night level rather than the ward level.

906 of 1,289 events on the 136 held-out rain days (**70.3%**) fall outside the
frozen top-20. Base rate among non-top-20 ward-days: **3.743%** (906 / 24,208).

| Feature | Mutual info | Point-biserial r |
|---|---:|---:|
| *n wards flooded tonight* (post-hoc) | 0.0259 | **0.294** |
| city rainfall | 0.0231 | 0.119 |
| own-cell rain_24h | 0.0165 | 0.116 |
| prior event count | 0.0049 | 0.113 |
| prior rank | 0.0102 | −0.105 |
| rain percentile | 0.0230 | 0.096 |
| rain_3h_max | 0.0115 | 0.091 |
| antecedent 7d | 0.0172 | 0.089 |
| ward area | 0.0075 | 0.075 |
| on the flood register | 0.0057 | 0.038 |
| bowl (centroid vs boundary elev.) | 0.0093 | −0.027 |
| elevation range | 0.0050 | 0.013 |
| season position | 0.0199 | −0.012 |
| elevation | 0.0072 | −0.007 |

Everything is significant because n = 24,208; nothing is large. The strongest
correlate is post-hoc *and* night-level — how many other wards flooded tonight.
That is the shape of the whole result.

I fetched ward elevation for this (Open-Meteo elevation API, free and keyless:
centroid plus 12 polygon-boundary samples per ward, 2,574 points, ~4 minutes
with backoff). Saved to `data/reference/ward_elevation.csv` since it is cheap
and M2 will want it. It ranks the right places qualitatively — the most
bowl-like wards are Shettyhalli, Horamavu, Ullalu, Bagalagunte and Bellandur,
several of them top-20 flood wards — but contributes nothing once memory is in
the model.

### (b) Where do the surprises sit in the prior-count ranking?

**Not concentrated at 21–40. Median rank 69.**

| Prior rank | Surprises | Share | Cumulative |
|---|---:|---:|---:|
| 21–40 | 215 | 23.7% | 23.7% |
| 41–60 | 194 | 21.4% | 45.1% |
| 61–100 | 195 | 21.5% | 66.7% |
| 101–198 | 302 | 33.3% | 100% |

Only **0.8%** come from genuinely cold wards (zero prior events) — this is
mid-ranked wards failing unpredictably, not unknown places appearing.

So the "trivial fix" hypothesis is dead. Lengthening the list trades precision
for recall: top-40 captures 46.1% of events at precision 10.92%, against
top-20's 29.7% at 14.08%.

### (c) Honest read on whether the 24 points are reachable

**No.** The decisive test: rank wards by their event count measured *on the test
period itself*. That is the best any static per-ward score could ever do,
whatever features produced it — drainage density, imperviousness, land cover,
anything.

| | precision@20 |
|---|---:|
| Honest static top-20 (trained to 2023) | 14.08% |
| **Cheating static top-20 (fitted on test)** | **15.66%** |
| Oracle with perfect per-night knowledge | 37.72% |

| | Points | Share |
|---|---:|---:|
| Headroom | 23.64 | 100% |
| Reachable by a perfect ward-level ranking | **1.58** | **6.7%** |
| Irreducibly within-ward / temporal | **22.06** | **93.3%** |

Corroboration: consecutive rain nights' event vectors correlate at **0.090** —
which wards flood tonight is nearly independent of which flooded last time. 161
of 178 non-top-20 wards produced at least one surprise, and the 20 most
surprise-prone hold only 30.8% of them. Spread thin, and it moves.

## 2. The thing I did not expect, and think matters most

**A good pooled AUC hides this problem completely, and the project was on
course to be fooled by it.**

A logistic model over all features reaches **held-out ROC-AUC 0.749**, PR-AUC
0.116 against a 0.037 base rate — a 3.1× lift. On its face that is a working
model. Its effect on precision@20 is **+0.18 points, Wilcoxon p = 0.84**.

The reason is a variance decomposition:

| Feature | Share of variance *between* nights |
|---|---:|
| season, city rainfall | 100% |
| antecedent 7d | 96.8% |
| own-cell rain_24h | 84.6% |
| rain percentile | 76.6% |
| own-cell rain minus city mean | 9.3% |
| area, elevation, bowl, prior count, register | **0%** |

Pooled AUC rewards separating bad nights from quiet ones. precision@k only
compares wards *within* one night. So:

| Model | Pooled AUC | Within-night AUC | precision@20 |
|---|---:|---:|---:|
| All features | 0.7487 | 0.7365 | 14.26% |
| Ward-varying features only | 0.7108 | 0.7398 | 14.19% |
| **Prior count alone** | 0.7060 | **0.7371** | **14.08%** |
| Night-level only | 0.6147 | **0.5000** | 4.71% |

A night-level model has within-night AUC of exactly 0.5 and scores at chance.
And every bit of within-night ordering comes from prior event count — adding
twelve features moves within-night AUC by −0.0006.

Written into `docs/01-evaluation-rules.md` as a rule: **never report a pooled
AUC on a location-day panel as evidence a triage model works.**

## 3. I tested the FMI features rather than assuming them

`docs/01-evaluation-rules.md` argued the headroom must come from memory
interacting with weather, and named `conditional_rate_at_current_band` and
`excess_over_city`. Both are cheap to build from prior data, so I built and
tested them instead of leaving them as a Phase 3 promise. Rates estimated on the
training window only, Laplace-smoothed toward the citywide rate per rainfall
band.

| Model | Within-night AUC | precision@20 |
|---|---:|---:|
| **prior_n alone** | **0.7371** | **14.08%** |
| prior_n + prior_rank | 0.7369 | 14.08% |
| conditional rate at band | 0.7091 | 12.94% |
| conditional rate + excess over city | 0.6979 | 12.79% |
| memory + interaction + terrain | 0.7332 | 13.82% |

**All worse than memory alone.** Conditional rate alone loses 1.14 points
(p = 0.041). Cause: `cond_rate` correlates with `prior_n` at **r = 0.853**,
`excess` at **r = 0.877**. Splitting a thin per-ward history across six rainfall
bands adds more estimation noise than interaction signal.

This exceeded the task's brief — you said "not building a model, asking whether
a signal exists". I judged it worth doing because these two features are the
stated premise of M3, they took twenty minutes, and finding out in Phase 3 that
the premise fails would be expensive. If you would rather this had waited for a
proper feature-engineering pass with more careful smoothing and more bands, the
scripts are in the scratchpad and it is easy to redo.

## 4. What I think this means for the project

Stated in profile §19.7, summarised here:

1. **Triage is bounded, and the bound is the contribution.** The static list is
   within 1.6 points of the best any ward-level ranking can achieve. "We
   measured how much a nightly triage list can be improved, and it is 1.6 of
   23.6 points" is a real finding, and more honest than a marginal win.
2. **Proof One needs restating.** As written it is close to unwinnable. The
   claim the data *does* support is the inverse: the event set genuinely moves
   (correlation 0.090), so a static list is not capturing a stable phenomenon,
   and yet nothing observable predicts the movement. I have put a
   "RESTATE THIS" block at the top of the Proof One section in the evaluation
   rules rather than rewriting it, since the restatement is your call.
3. **Weight shifts to the Learn outputs.** Emerging detection and intervention
   effectiveness use accumulated ward history, not nightly ordering, so this
   result does not touch them. They are also the more original contributions.
4. **Build M0–M3 to demonstrate the bound, not to beat it.** All four landing
   near 14% against a 37.7% ceiling *is* the result; the ablation is what makes
   it credible.

## 5. What I want a second opinion on

1. **Whether to restate Proof One now or after the mid-review.** I left the
   original text in place with a restatement block above it. Rewriting it is a
   bigger decision than a doc edit — it changes what the project promises — and
   it should be yours.
2. **Whether the label is the real ceiling.** A complaint is a citizen report,
   not an observed flood. Some fraction of the 22 irreducible points is
   certainly label noise rather than missing features, but I cannot separate
   the two with this data. If you think that fraction is large, it is worth
   saying so explicitly in the limitations rather than letting a reader assume
   the 22 points are physical.
3. **Whether location-level would change the answer.** Everything here is
   ward-level. The register has ~390 points and a location is far smaller than
   a ward, so per-location the base rate falls and the panel gets sparser — I
   would expect the same conclusion more strongly, but it is untested and the
   complaint-to-location join does not exist. Worth deciding whether to spend
   on that join at all, given this result.
4. **Whether to keep chasing terrain.** `imperviousness` and `drain_distance_m`
   are in the schema and unpopulated. §19.6 says no static ward feature can add
   more than 1.6 points total, so populating them cannot pay off for *triage*.
   They may still matter for the Learn outputs and for the paper's credibility.
   I would not spend on them now; say if you disagree.

## 6. Things a future reader should not have to rediscover

- **Open-Meteo's elevation API rate-limits hard.** 26 batches of 100 points
  triggered a 429 without backoff. It is free and keyless but needs ~2s spacing
  and exponential retry.
- **`cond_rate` and `prior_n` correlate at 0.85.** Any "interaction" feature
  built by conditioning a sparse per-ward history on weather bands will largely
  restate the base rate with extra noise. Check the correlation before
  believing an interaction feature is new information.
- The frozen top-20 and the cheating top-20 share **13 of 20** wards. The
  static list is close to optimal *as a list*; the problem is not its
  membership.

## 7. Verification

57 tests pass (unchanged — this task added analysis, not pipeline code).
`data/reference/ward_elevation.csv` is new and committed. Database unchanged:
`locations` 596, `weather_observations` 1,309,896, `weather_daily` 54,579.

Temporal discipline throughout: prior counts for the fit set from
2020-02-08 → 2022-12-31, for the test set from 2020-02-08 → 2023-12-31; models
fit on 2023 rain days, evaluated on the 136 rain days of 2024-01-01 →
2025-06-19. The single exception is §19.6, where the leakage is the instrument.
