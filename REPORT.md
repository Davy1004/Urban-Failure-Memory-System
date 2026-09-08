# REPORT — closing the analysis: Q5 and the targeting objection

Task: NEXT.md "close the analysis, then stop". Completed 2026-09-08.
**This is the last analysis report.**

**Q5: both hypotheses are wrong, and so was the premise. There is no reversal to
explain. Only the lowest-spend quintile differs from zero (p = 0.022); Q5's
+0.105 has a CI of [−0.142, +0.353], p = 0.385; and a quadratic term in log
spend is not significant (F = 1.26, p = 0.265). §25.5 over-read its own table.**

**Targeting: settled exactly as you predicted. Spend versus absolute events is
ρ = +0.274 raw, and −0.050 (p = 0.603) controlling for ward area. The
correlation is entirely area.**

Full write-up: profile §26.

---

## 1. The development confounder — tested and rejected

You thought this the likelier explanation. It is not there.

| | ρ | p |
|---|---:|---:|
| log spend vs log complaint-volume growth | −0.112 | 0.243 |
| log volume growth vs Δ index | −0.032 | 0.742 |

And the quintiles are flat in growth — **Q5 wards grow no faster than Q1 wards:**

| Quintile | Median spend | **Median volume growth** | Mean Δ |
|---|---:|---:|---:|
| Q1 | ₹3.1 M | 1.94× | +0.232 |
| Q2 | ₹10.4 M | 1.95× | +0.108 |
| Q3 | ₹20.2 M | **2.19×** | −0.146 |
| Q4 | ₹60.6 M | 2.02× | −0.162 |
| **Q5** | **₹167.2 M** | **1.98×** | +0.105 |

Adding log volume growth to the main specification:

| Term | Baseline | With development control |
|---|---:|---:|
| **log(1+spend)** | **−0.0240** (p = 0.0138) | **−0.0247** (p = 0.0118) |
| log(volume growth) | — | −0.1065 (p = 0.458) |
| R² | 0.531 | 0.533 |

Growth-adjusted quintile deltas are unchanged to three decimals (Q5
+0.105 → +0.102). Jakkur and Someshwara *are* development corridors, but they do
not carry the quintile.

## 2. The disruption hypothesis — also rejected

| Quintile | Pre | 2023 | 2024–25 | Δ(2023) | Δ(24–25) |
|---|---:|---:|---:|---:|---:|
| Q3 | 1.13 | 1.06 | 0.93 | −0.073 | −0.205 |
| Q4 | 1.22 | 1.02 | 1.08 | −0.197 | −0.134 |
| **Q5** | 1.13 | 1.25 | 1.22 | **+0.122** | **+0.092** |

Q5 does not recover. Paired within Q5, 2024–25 versus 2023 is **−0.030,
p = 0.834**. Neither period differs from pre (p = 0.340, 0.539). Re-estimating
separately, the spend coefficient is stable — **−0.0243 (p = 0.025)** on 2023,
**−0.0238 (p = 0.065)** on 2024–25. No disruption signature.

## 3. Why both failed: there was nothing to explain

I should have checked this before testing either hypothesis. Per-quintile means
with CIs:

| Quintile | n | Mean Δ | 95% CI | p vs 0 |
|---|---:|---:|---|---:|
| **Q1** | 21 | **+0.232** | [+0.038, +0.425] | **0.022** |
| Q2 | 20 | +0.108 | [−0.228, +0.444] | 0.508 |
| Q3 | 21 | −0.146 | [−0.308, +0.015] | 0.073 |
| Q4 | 20 | −0.162 | [−0.474, +0.150] | 0.291 |
| **Q5** | 21 | **+0.105** | **[−0.142, +0.353]** | **0.385** |
| Untreated | 7 | +0.251 | [−0.778, +1.280] | 0.572 |

**Only Q1 is distinguishable from zero.** And a quadratic term in log spend
gives +0.0021 (p = 0.265), F-test for the added term **F = 1.26, p = 0.265** —
**no statistical evidence of non-monotonicity at all.**

The quintile means are a noisy discretisation of 110 wards into bins of ~20. The
linear estimate uses every ward and is the reliable one.

**So §25.5's instruction was half right.** Publish the table — but *with* its
confidence intervals, which show the U-shape is not real. I have corrected the
profile and the rules file rather than leaving the stronger claim standing.

That is the second time in this project that an appealing pattern failed on
proper testing (after the register contradiction). Both are now recorded with
their tests visible.

## 4. One deflation you should see

The effect is significant **conditional on the controls**, not as a raw
association:

| | ρ | p |
|---|---:|---:|
| Spearman(spend, Δ index), treated wards | −0.163 | 0.099 |
| Spearman(spend, Δ index), untreated as spend = 0 | −0.175 | 0.067 |

The main specification reaches p = 0.014 by controlling for the pre-period
index, which carries strong mean reversion (−0.788, p < 0.0001). Controlling for
it is correct — regression to the mean would otherwise swamp everything — but it
means **a raw scatter of spend against outcome shows only a marginal trend**. A
reader who plots it will not see the result. Better we say that than they
discover it.

## 5. The targeting objection — settled

| | ρ | p |
|---|---:|---:|
| Spend vs absolute events, raw | +0.274 | 0.0038 |
| **Spend vs absolute events, controlling for ward area** | **−0.050** | **0.603** |
| Spend vs ward area | +0.474 | <0.0001 |
| Absolute events vs ward area | +0.649 | <0.0001 |
| Spend vs relative index, controlling for area | +0.051 | 0.599 |

**The partial correlation collapses.** Area fully explains the association. Your
predicted framing holds, and I have written it into the rules file in the order
you specified:

> Drainage spend tracks ward area (ρ = +0.474). It correlates with absolute
> complaint counts (ρ = +0.274) because large wards generate more complaints of
> every kind — controlling for area, that correlation vanishes (ρ = −0.050,
> p = 0.60). Benchmarked against each ward's own complaint mix, allocation is
> uncorrelated with need (ρ = +0.051, p = 0.60).

"BBMP targets absolute complaint volume" is dead, not deflected.

## 6. Where the analysis closes

| Output | Result |
|---|---|
| **Triage** | Ceiling measured: 1.58 of 23.64 points reachable by any ward-level score; static list 14.08% against a 37.72% oracle. |
| **Emerging** | Real in aggregate (permutation p = 0.0010), one nameable ward (Jakkur). Finds *chronically above norm*, not *accelerating*. |
| **Effectiveness** | **Positive:** −0.0240 per log rupee, p = 0.0138, n = 110, monotone, targeting confound measurably absent. |

**No new analysis threads.** The queue is building only.

## 7. What I want a second opinion on

Only one thing, and it is small.

**Whether §25.5 should be edited or annotated.** I edited it — the profile and
rules now say the non-monotonicity is not real, with §26 carrying the working.
The alternative was to leave §25.5 intact and let §26 correct it, preserving the
sequence of reasoning the way the retraction in §25.7 is preserved. I chose
editing because §25.5 contained an *instruction* ("never publish the coefficient
without the quintile table") that would have propagated a wrong emphasis into
the paper, whereas §25.7's retraction was a claim, not an instruction. If you
prefer the other convention, it is a two-line change.

I have no other open questions. The design note for Phase 4 in NEXT.md is clear
and I have carried it into the queue.

## 8. Verification

57 tests pass. Database unchanged — still Phase 0 plus weather.

`data/reference/ward_dose_response_panel.csv` regenerated with the extra columns
this analysis needed: `p23`, `p45`, `d23`, `d45` (post-window split), `growth`,
`log_growth`, `ev_all`.

Method: same relative index and panel as §25. Partial correlations computed on
ranks (Spearman) by residualising both variables on log ward area. Quadratic
test is a nested F-test on the added term. Quintile CIs are t-intervals on the
mean, n ≈ 20 per bin.
