# REPORT — 10 September 2026 (fourth session)

Task: close the three verifiable figures still open, then stop.

**All three closed. None of them resisted.** The verifier goes from 65 figures
to **90** (94 with `--slow`). One commit, `661e91f`, pushed. 148 backend tests,
31 frontend tests, 27/27 parity.

Read-only recomputation and documentation edits, as specified — no schema, no
endpoints, no screens, no behaviour.

---

## 1. The register agreement (profile §21)

Done first, as instructed. **It reproduces exactly — nine of its ten figures to
the last digit.**

| | documented | measured |
|---|---:|---:|
| Frozen top-20 on the register | 16 / 20 | **16 / 20** |
| Register coverage, 198 wards | 52% | **51.52%** |
| Expected under independence | 10.3 | **10.303** |
| Hypergeometric p | 0.0060 | **0.0060** |
| Mean events, register wards | 24.7 (median 13) | **24.71 (13)** |
| Mean events, non-register | 13.4 (median 7) | **13.40 (7)** |
| Spearman ρ, events vs register points | 0.334 (p = 1.5e-06) | **0.3343 (1.49e-06)** |
| Kendall τ | 0.265 (p = 1.4e-06) | **0.2650 (1.37e-06)** |
| Mann-Whitney one-sided p | 0.0001 | **0.000113** |
| The four off-register top-20 wards | Hoodi, Someshwara, Jakkur, Basavanapura | **exactly those four** |

The window matters and is now part of the check: these are all on the **train**
window (2020-02-08 … 2023-12-31), the frozen list's own. Scored on the full
window instead, every figure moves — the means go to 38.6 against 21.9 and ρ to
0.354. That is precisely the kind of basis slip the evaluation rules exist to
catch, so `_register()` pins the window explicitly.

### The one figure that does not reproduce — and it is not a wrong number

**"Overlap of the two top-20 lists: 9/20" is not a well-defined quantity.**

I got 10, so I went looking for the tie-break rather than assuming a
discrepancy. Register points per ward is a small integer, and the ranking is
tied exactly at the cut:

- **10** wards hold strictly more than the 20th-place value of 3 points;
- **16** wards are tied at exactly 3.

So "the top 20 by register points" means taking 10 arbitrary wards out of 16, and
the overlap can be **anywhere from 6 to 11 of 20** depending purely on which. The
documented 9 and the 10 a plain `nlargest` produces are both legitimate values.
By contrast the events ranking is barely tied at all — 19 wards strictly above
the cut, 2 tied.

I recorded it as a caveat rather than changing the number, because there is no
correct number to change it to. `docs/02` now shows the figure as 9–10 with the
tie explained.

**It does not weaken the §21 reading; it slightly strengthens it.** Even the
tie-break most favourable to agreement gives 11/20, so the two rankings really do
disagree on severity ordering — which is exactly the claim the paragraph makes.
But it must not appear on a slide as a single number, and the stable figures
(16/20, p = 0.0060, ρ = 0.334, τ = 0.265) carry the argument on their own.

---

## 2. The §26 quintile table

**Reproduces perfectly. Every cell.**

All five quintile n (21/20/21/20/21), all five means, **all five 95% confidence
intervals**, all five p-values, and the untreated row (n = 7, +0.251,
[−0.778, +1.280], p = 0.572). Q1 is the only one distinguishable from zero
(+0.232, [+0.038, +0.425], p = 0.022); Q5's +0.105 has a CI spanning zero
(p = 0.385).

The CIs are pinned as well as the means, deliberately — `DECISIONS.md` says this
table must never be published without them, and a check on the means alone would
let the intervals drift unnoticed.

The quadratic test reproduces too: coefficient **+0.0021**, **F = 1.2575,
p = 0.265**. There is no statistical evidence of non-monotonicity.

**This independently confirms the specification I recovered last session.**
§26.1 carries its own coefficient table, and it lists `pre` = −0.7877,
`log(area)` = −0.0033 and R² = 0.531 — which is exactly
`delta ~ log_spend + log_area + pre`. I found the specification by search; the
profile had been quietly holding the evidence for it in a different section all
along. The growth-control model reproduces as well (log_spend −0.0247,
p = 0.0118; log_growth −0.1065, p = 0.458; R² 0.533).

Two independent routes to the same specification is a much better position than
one recovered by search, and it means the answer to "what did you control for?"
is now both correct and citable.

---

## 3. The 22% — it reproduces, and the instrument was the missing piece

You were right that this was worth chasing rather than replacing.

I tried eleven instruments on the citywide event share across the 20 quarters:

| instrument | change |
|---|---:|
| first quarter vs last quarter | −58.6% |
| **pooled first 4 vs last 4 (events ÷ complaints per block)** | **−21.8%** |
| mean of per-quarter shares, first 4 vs last 4 | −20.6% |
| median of per-quarter shares, first 4 vs last 4 | −17.1% |
| first 4 vs last 4, dropping the final quarter | −23.8% |
| first half vs second half (10 quarters each) | −35.0% |
| OLS fit, endpoint to endpoint | −38.9% |
| Theil–Sen fit, endpoint to endpoint | −35.3% |
| OLS on log(share), total change | −43.8% |
| Theil–Sen on log(share), total change | −39.5% |
| pooled events/complaints, half vs half | −36.7% |

**The pooled first-four against last-four gives −21.8%, which is the documented
22%.** Total events over total complaints in each block — 862/100,990 against
1,533/229,747.

That instrument is not a guess: it is exactly what
`data/reference/ward_relative_trends.csv` is built around, whose columns are
`ev_first4, ev_last4, co_first4, co_last4, rel_first4, rel_last4`. First-four
against last-four is already this project's standard comparison, so the citywide
figure was computed the same way as every per-ward figure beside it. My earlier
−20.6% took the mean of the per-quarter shares — a different estimator on the
same series, which is why it was close but not equal.

**The figure stays at 22% and the instrument now travels with it**, in all four
places it appears: `CLAUDE.md`, `DECISIONS.md`, `docs/01-evaluation-rules.md`
and the profile. I did not touch the two unrelated "a precision@20 of 22%"
sentences, which are a hypothetical illustration of a different quantity.

One thing worth knowing but not worth changing: the decline is **not a
statistically significant monotonic trend** over the 20 quarters (Kendall
τ = −0.232, p = 0.165). That does not undermine the argument it supports — the
point is that the city baseline is not zero, and a −22% shift is large enough to
flip Proof Two's verdict from 0 rising to 9 rising regardless of whether the
quarter-to-quarter path is monotone.

---

## 4. What is in the verifier now

**90 figures, 94 with `--slow`.** Up from 65. The three closed items added 25
checks between them, including every cell of the quintile table with its
intervals, the whole §21 table, and the citywide decline with its instrument
documented in the function that computes it.

Still not covered, and now down to **eight** items — all in
`docs/02-data-profile.md`, all from sessions whose scripts were never committed:

| Figure | To check it |
|---|---|
| Pooled AUC 0.749 vs within-night 0.737 | Refit the ranking model. The model is not built. |
| Weather-only ranking 5.63% | Rank wards by cell rainfall per night; the exact feature was never recorded. |
| Per-ward rainfall lift (3.06 → 3.00, χ² p = 0.877) | Re-run the lift computation on both grids. Data present, script gone. |
| Permutation null: 9 rising / 4 declining, p = 0.0010 | Re-run 2,000 permutations. Seed unrecorded, so p will be close, not identical. |
| Magnitude R² = 0.196, 3-class 50.0% vs 39.6% | Refit the magnitude model. |
| §28 gate figures (ρ = +0.505, 6 of 8 quarters, 51 of 196 wards) | Re-run the gate analysis off the raw work orders. |
| Palette contrast ratios (2.06:1 … 2.21:1) | Re-run the data-viz palette validator, which is not in the repo. |
| "309,012 rows, 40.31%" for the 96 off-register wards | A **pre-filter** number — 40.31% of the 766,648 raw grievance rows, not of the 237,157 loaded. Post-filter the same wards hold 98,156 = 41.39%. `DECISIONS.md` says "40% of the data", true either way, so left alone. |

None is a headline. Everything the paper and the screens rest on is now checked.

---

## 5. Judgement calls

1. **I left the 9/20 overlap as a caveat rather than picking a number.** There is
   no correct value to pick — the quantity is tie-dependent by construction. If
   you would rather the profile state a single figure with a declared tie-break
   (alphabetical, say), that is a one-line change, but I think "approximately
   9–10, and here is why it cannot be exact" is the more honest thing for a
   research log to say.

2. **The 22% stays at 22%, not −21.8%.** The documented figure is a rounded form
   of the reproducible one, and rounding is not an error. Changing it to −21.8%
   would have gained precision the underlying data does not warrant and broken
   every place the paper says 22%.

3. **I did not touch anything below "Answers to your questions" in `NEXT.md`**,
   as asked. Nothing in those sections looked wrong to me on this reading.

---

## 6. State

- `origin/main` at `661e91f`; working tree clean; nothing unpushed.
- **148 backend tests, 31 frontend tests**, `npm run build` clean.
- `scripts/check_parity.py --base http://127.0.0.1:8000` → **27/27, PASSED**.
- `scripts/verify_documented_figures.py --slow` → **94/94, PASSED**.
- The demo recording, the runbook, the deploy path and the parity gate are all
  unchanged from the previous sessions and all still pass.

**The freeze is now absolute on my side. Nothing is queued for before the 16th.**
What remains is Tanmay's: the supervisor on the 14th, names on the paper and on
slides 1 and 14, and the reference volume and page numbers.
