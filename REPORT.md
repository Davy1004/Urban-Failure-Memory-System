# REPORT — intervention effectiveness, plus the two fixes

Task: NEXT.md "intervention effectiveness, plus two cheap fixes". Completed
2026-09-08.

**The dose-response works and it is the project's one positive quantitative
result: −0.0240 on log drainage spend, p = 0.0138, 95% CI [−0.0428, −0.0052],
n = 110 wards.**

**The surprise is that reverse causality — which you called "the whole problem"
— is measurably absent. Spend versus the pre-period relative index is r = −0.083
(p = 0.39). BBMP's drainage spend tracks ward AREA (ρ = +0.474), not flooding
need. That makes this a much better-identified estimate than expected.**

**Two things you should not miss: the response is not monotone (the top spend
quintile got worse), and §24's register-contradiction claim is retracted — it
was a four-ward coincidence, p = 0.79 across all 198.**

Full write-up: profile §25.

---

## 1. (a) Wards 184–198 recovered

The proxy was validated before being trusted, as you asked. On the 183
main-schema files, which carry both `End Date` and the BR/CBR dates:

| Candidate | n | Median offset from End Date | Within 90 d | Same year |
|---|---:|---:|---:|---:|
| **BR Date** | 42,560 | **+22 d** | **76.2%** | **83.2%** |
| CBR Date | 29,621 | +621 d | 6.4% | 13.3% |
| Order Date | 43,465 | −92 d | 44.6% | 60.5% |

**BR date is the right proxy.** CBR is the bill-clearance date about two years
later and would have been badly wrong — worth knowing, since it is the second
date in the string and an obvious thing to grab.

Recovery: 4,178 legacy rows, 100% with at least one date, 44.0% drainage,
yielding **125 additional drainage works across the 15 missing wards** in the
study window. Small in works, but it restores Bilekahalli, Begur, Gottigere and
Arakere to the panel, which was the point.

## 2. (b) You were right — the instrument was wrong

Slope persistence is not the test. Level persistence is, and it holds.

| Flag rule (first 10 quarters) | n | Mean level 1st half | 2nd half | vs other wards |
|---|---:|---:|---:|---:|
| p < 0.20 | 10 | 1.01 | 1.23 | p = 0.380 |
| **top 10 by first-half slope** | 10 | 1.42 | **1.77** | **p = 0.0001** |
| top 20 by first-half slope | 20 | 1.37 | 1.45 | p = 0.0051 |

**All 10 top-flagged wards ended above the city norm; 8 of 10 rose in level**,
against 53% of eligible wards.

Note I had to change the flagging rule to make this testable: only **one** ward
clears p < 0.05 on ten quarters, so I used rank-based flags. That is what a
detector would actually do, but it is a deviation worth seeing.

**The control you would have asked for next:** is this just "already-bad wards
stay bad"? No. First-half slope and level are nearly independent (ρ = 0.132),
and slope-flagging beats level-flagging (second-half mean **1.77 vs 1.45**,
against 1.16 for all wards). In OLS of second-half level on first-half level and
slope, slope enters at **p = 0.051**, adding R² +0.030.

**But** flagged wards do not significantly exceed their *own* first-half level
(p = 0.23). So the detector finds **chronically above norm**, not
**accelerating**. The claim should be stated that way and no stronger.

## 3. The main result

Design as specified: Δ(relative index, post − pre) on log drainage spend, with
pre-period index and log ward area as controls.

- Window 2021-01 → 2022-12 (1,353 main-schema + 125 recovered works).
- Pre 2020Q2–Q4, post 2023Q1–2025Q1.
- **n = 110 wards** with ≥8 strict events. **103 treated, 7 untreated** — your
  read was right, treated-vs-control does not exist.

| Specification | Coef on log spend | se | p | 95% CI |
|---|---:|---:|---:|---|
| Control for pre-index + log area | **−0.0240** | 0.0096 | **0.0138** | [−0.0428, −0.0052] |
| Spend residualised on pre-index | **−0.0240** | 0.0096 | **0.0137** | [−0.0428, −0.0052] |

R² = 0.531. Pre-period index enters at −0.788 (p < 0.0001) — strong mean
reversion. A tenfold spend increase maps to about a **0.055** fall against a
city norm of 1.00.

### Your point 1 — reverse causality

**I did both specifications and they are identical, because there is nothing to
residualise.**

**corr(pre-period relative index, log spend) = −0.083, p = 0.39.**

| Spend correlates with | ρ | p |
|---|---:|---:|
| **Ward area** | **+0.474** | <0.0001 |
| Absolute strict event count | +0.355 | 0.0001 |
| **Relative flooding index (pre)** | **+0.082** | **0.392** |

| Spend quartile | n | Median events | Median area km² |
|---|---:|---:|---:|
| Q1 low | 28 | 16 | 1.95 |
| Q4 high | 28 | 28 | 7.05 |

**Spend tracks ward size.** It correlates with raw counts because big wards
generate more of everything; benchmarked against each ward's own complaint mix,
the relationship vanishes.

I checked whether this is a budget formula — it is not. Only 20% of works (14%
of spend) sit under explicitly per-ward heads; the rest are Zone Works,
Mayor-sanctioned, or Minister discretionary grants. **Allocation is
discretionary and still uncorrelated with relative flooding need.** That is a
better institutional-memory finding than the one §24 proposed, and unlike that
one it survives testing.

### Your point 4 — effective n

**n = 110 wards**, from 1,478 drainage works. The binding constraint is not the
works but the ≥8-event eligibility filter: 88 of 198 wards have too few strict
events across pre and post to estimate a change.

## 4. The problem with the result

**The dose-response is not monotone.**

| Quintile (treated) | n | Median spend | Mean pre | Mean post | **Mean Δ** |
|---|---:|---:|---:|---:|---:|
| Q1 | 21 | ₹3.1 M | 1.01 | 1.24 | **+0.232** |
| Q2 | 20 | ₹10.4 M | 0.98 | 1.08 | **+0.108** |
| Q3 | 21 | ₹20.2 M | 1.13 | 0.99 | **−0.146** |
| Q4 | 20 | ₹60.6 M | 1.22 | 1.06 | **−0.162** |
| **Q5** | 21 | **₹167.2 M** | 1.13 | 1.24 | **+0.105** |
| Untreated | 7 | ₹0 | 1.39 | 1.64 | +0.251 |

Q1→Q4 falls cleanly and untreated wards are worst of all — which is the story.
**Then Q5 reverses.** The linear coefficient is carried by Q1–Q4.

You said the scatter would be worth more than the coefficient in the paper. It
is, and not in the way either of us expected: it shows the effect *and* its
limit. Three candidate explanations, none tested — targeting operating at the
extreme even though absent on average; large works disrupting drainage during
construction; or the biggest-spend wards being rapid-development corridors where
the problem outgrows the works. Jakkur and Someshwara, the top two spenders, fit
the third.

## 5. Your point 2 — Jakkur, dated

| | Pre (2020) | During works (2021–22) | Post (2023–25) |
|---|---:|---:|---:|
| Mean relative index | **0.55** | 0.93 | **1.42** |
| Drainage spend | ₹346 M | ₹494 M | — |

**The spend came first.** First drainage spend 2020Q2; first quarter above the
city norm 2021Q2. Cross-correlation of spend against index is negative at every
lag (k=2: −0.53). Trend over 20 quarters: Spearman +0.586, p = 0.0066.

**So "the works were a response to deterioration already under way" is not
supported for Jakkur.** ₹840 M went in and the ward went from about half the
city norm to about 1.5×.

**One caveat that matters:** the work-orders dataset ends in 2022, so the blank
spend after 2022Q1 is censoring, not evidence BBMP stopped. What is supportable
is that within the observable window the money preceded the deterioration.

The quarter-by-quarter series is in profile §25.6 and is the chart you wanted.

## 6. Your point 3 — the register contradiction does not hold

I tested it properly and **it fails.**

| | n | Median spend | Mean spend |
|---|---:|---:|---:|
| On the flood register | 102 | ₹17.3 M | ₹43.9 M |
| Not on the register | 96 | ₹16.6 M | ₹44.8 M |

Mann-Whitney (off > on) one-sided **p = 0.789**. Top-20 spenders off the
register: **9 of 20** against a 48% base rate, hypergeometric **p = 0.713**.

The §24 observation was three wards out of four, and four wards is not evidence.
I have marked it retracted in the profile and the rules file. This is the one
place in this project where an appealing sentence did not survive contact with
the full sample, and it is worth keeping visible for exactly that reason.

The surviving and stronger version is §25.3: **drainage spend tracks ward area,
not relative flooding need.**

## 7. What I want a second opinion on

1. **Whether Q5 needs explaining before this is publishable.** I can test the
   "large works disrupt during construction" hypothesis by splitting the post
   window into 2023 and 2024–25 — if Q5 recovers later, that is disruption
   rather than failure. It is maybe an hour and it would materially strengthen
   or weaken the result. I did not do it because the brief was the main design.
2. **How hard to push "targeting is absent".** It is the most surprising finding
   here and it is what makes the estimate credible, but it rests on the *relative*
   index. Spend does correlate with absolute counts (ρ = +0.355). A reviewer
   could argue BBMP targets absolute complaint volume, which is a form of
   targeting even if it is not targeting my outcome variable. I think the
   specification is still clean, but the framing needs care.
3. **Whether to stop the analysis here.** Your scheduling note said the queue
   should turn to building after this lands. It has landed. I agree and have
   restructured the queue accordingly, with the complaints loader promoted and
   analysis items pushed below it. Confirm and I will not open another analysis
   thread.

## 8. Verification

57 tests pass (analysis only). Database unchanged — still Phase 0 plus weather.

New committed artifacts: `data/reference/ward_dose_response_panel.csv` (110-ward
panel: pre/post index, event counts, spend, works, area, register flag) and
`data/reference/ward_persistence.csv` (first/second-half slopes and levels).

Method: relative index `events / (complaints × city_share)` with +0.5 smoothing,
20 complete quarters. Drainage classified by keyword on `Name of Work` — a
hand-curated map is still owed and is queued. Legacy dates via BR date, validated
at 76.2% within 90 days. OLS with analytic standard errors; no clustering, since
the unit of observation and the unit of treatment are both the ward.
