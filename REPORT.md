# REPORT — Proof Two re-tested against the right null; work orders feasible

Task: NEXT.md "Proof Two may not be dead; the null is wrong", plus the
work-orders feasibility check. Completed 2026-09-08.

**You were right. The null was wrong and it manufactured the negative.
Against the city trend the same data gives 9 rising wards instead of 0, and a
permutation test puts that at p = 0.0010.**

**But multiple testing bites: Benjamini–Hochberg leaves zero nameable wards
across all 103, and exactly one — Jakkur — under the pre-specified non-register
restriction. Proof Two can demonstrate its method on one validated case. It
cannot yet hand a city a defensible list.**

**And the work orders are feasible and better than expected: ~1,350 usable
drainage works across 166 wards, with ward, date and cost complete for 183 of
198 wards.**

Full write-up: profile §23 (re-test) and §24 (work orders).

---

## 1. The correct null (your step 1)

I used the **ratio** form, as a standardised incidence ratio:

```
rel(w,q) = events(w,q) / [ complaints(w,q) × city_share(q) ]     (+0.5 smoothing)
```

`rel = 1` means the ward sits exactly at the city norm that quarter. Theil–Sen
slope plus Mann-Kendall on `rel`. I chose the ratio over slope-differencing
because it yields a per-quarter series that is directly interpretable and can be
plotted, and because the smoothing handles zero-event quarters cleanly.

Citywide reference: share 0.854% → 0.667%, Theil–Sen −0.000094/quarter,
Mann-Kendall **p = 0.0104**. The city trend is real and downward — which is
precisely why zero was the wrong benchmark.

## 2. The same table again (your step 2)

103 wards with ≥15 strict event-days, 20 complete quarters:

| Test | Rising | Declining |
|---|---:|---:|
| Raw event count | 7 | 3 |
| Normalised share, null = **zero** (§22) | **0** | 10 |
| Normalised share, null = **city trend** | **9** | 4 |

The nine, with register membership:

| Ward | On register | rel slope | p | rel first4 → last4 | events |
|---|---|---:|---:|---|---:|
| **Jakkur** | **NO** | +0.0603 | **0.0047** | 0.55 → 1.17 | 97 |
| Chowdeshwari Ward | NO | +0.0368 | 0.0237 | 0.61 → 2.00 | 16 |
| Dharmarayaswamy Temple Ward | yes | +0.0735 | 0.0283 | 0.92 → 2.57 | 53 |
| Bharathi Nagar | yes | +0.1454 | 0.0283 | 1.06 → 4.97 | 46 |
| Kempegowda Ward | yes | +0.0758 | 0.0283 | 0.78 → 1.80 | 43 |
| Bommanahalli | yes | +0.0559 | 0.0336 | 0.53 → 1.63 | 29 |
| Jalahalli | NO | +0.0270 | 0.0398 | 0.79 → 2.09 | 20 |
| Sudam Nagar | NO | +0.0465 | 0.0398 | 1.15 → 1.86 | 23 |
| Vijanapura | yes | +0.0376 | 0.0398 | 0.32 → 1.54 | 19 |

**So Proof Two is alive and the earlier zero was a null of construction, exactly
as you suspected.**

## 3. What I added, because nine is not obviously more than five

103 tests at p < 0.05 gives ~5 false positives by chance. I did not want to
report nine as a finding without checking, so:

**Permutation null** — shuffle each ward's quarters in time, preserving each
ward's distribution and the city benchmark, 2,000 draws:

| | |
|---|---:|
| Rising wards under the null | mean **2.4**, sd 1.6, 95th pct 5, max 9 |
| Observed | **9** |
| **Permutation p for ≥9 rising** | **0.0010** |

**The aggregate excess is real.**

**Benjamini–Hochberg FDR**, one-sided rising hypothesis:

| Population | q=0.05 | q=0.10 | q=0.20 |
|---|---:|---:|---:|
| All 103 eligible wards | 0 | 0 | 0 |
| **42 non-register wards** (pre-specified pool, §12.5) | 0 | **1 (Jakkur)** | **1** |
| 61 register wards | 0 | 0 | 0 |

**Split-half stability**: slopes on the first vs second ten quarters correlate at
**ρ = 0.035**, 4/10 top-riser overlap. Partly power — ten quarters is thin — but
it means *which* ward is rising is unstable.

So the honest statement has two halves that must travel together: **more wards
are diverging upward than chance allows (p = 0.001), and almost none can be
named individually.** That is the same shape as §19 — real aggregate signal,
poor per-unit identifiability — which is now the third time this project has
landed there.

I lean on the non-register restriction being legitimate because §12.5 fixed that
population before any of this was measured. It must be declared as pre-specified
in the write-up or it is fishing.

### Jakkur

Events 6 → 35 while its own complaints went 1,411 → 4,396. Relative index
0.55 → 1.17. Events grew 5.8× against 3.1× reporting growth, so it is outpacing
its own channel — exactly what the normalisation is for. Off the register, so a
genuine "failing but not yet official" candidate. It is first on raw growth,
fourth on the zero null, first on the city null, and the only FDR survivor.

## 4. Question 3 settled (your step 3)

Under the correct null only four wards decline — and **all four fell in absolute
terms**, in a city where absolute events rose 78% (862 → 1,533) and complaints
rose 128%:

| Ward | Events first4 → last4 | Complaints first4 → last4 | rel |
|---|---|---|---|
| Bagalagunte | 10 → 4 | 783 → 1,433 | 1.32 → 0.52 |
| A.Narayanapura | 12 → 4 | 356 → 757 | 2.68 → 0.91 |
| Padmanabha Nagar | 4 → 3 | 580 → 1,476 | 0.83 → 0.43 |
| Ramamurthy Nagar | 25 → 13 | 1,679 → 2,998 | 1.76 → 0.71 |

**Improvement is on the table for these four**, and cannot be a denominator
effect since absolute counts fell while volume doubled.

The contrast justifies your instruction. Of the ten wards that "declined"
against the **zero** null, four had absolute events **rise** — Hoodi 25→32,
Horamavu 43→46, Varthur 15→27, Vishwanathnagenahalli 7→8. Pure denominator
growth. The zero-null test could not distinguish those from real reduction; the
city null does.

## 5. Work orders — feasible (your second task)

198 CSVs, one per ward, 27 MB. **The one number: ~1,350 usable drainage works
across 166 wards.**

| Completion window | Before / after | Drainage works | Wards | Median cost |
|---|---|---:|---:|---:|
| 2020-08 → 2022-12 | 6m / 2.5y | 1,894 | 177 | ₹3.53 M |
| **2021-01 → 2022-12** | **11m / 2.5y** | **1,353** | **166** | ₹3.92 M |
| 2021-07 → 2022-12 | 17m / 2.5y | 728 | 145 | ₹3.96 M |

**Fields:** ward 100%, cost 100%, parseable dates 95.0%. Drainage is separable
and is the largest work type at **36.4%** of 45,737 rows (roads 20.0%, buildings
13.1%, water/sewer 8.4%, electrical 7.5%).

**Two real problems, neither fatal:**

- **Wards 184–198 are unusable.** 15 files carry a legacy schema
  (`id, wo num, wodetails, contractor, brnumber, amount, nett, deduction`) with
  **no date column** — dates are buried inside a concatenated `brnumber` string
  — and the works are 2014–2016, predating the complaint window. That is the
  whole high-numbered Bommanahalli/South block.
- **Completion counts thin exactly where the complaint window opens**: 6,138 in
  2018, 4,333 in 2020, 3,386 in 2021, 993 in 2022.

**The design problem is the inverse of the one you anticipated.** Treated-vs-
control fails because **166 of 198 wards were treated** — only 32 untreated, and
those are plausibly wards BBMP judged needed nothing, so not exchangeable. But
spend varies hugely (median ₹19.5 M, max ₹631.6 M), so **dose-response on spend
is the right design** and a stronger one.

**Two observations that came free:**

Three of the four register-absent wards from §21 are top-four drainage spenders
— Someshwara ₹631.6 M, Jakkur ₹494.2 M, Basavanapura ₹370.4 M. BBMP is spending
heavily on drainage in wards its own flood register does not list.

And **Jakkur — the single FDR-surviving emerging ward — is the second-highest
drainage spender.** Its flooding share rose significantly while ₹494 M was spent
there. Either the works did not work, or the works were a response to a
worsening problem. Separating those is exactly what intervention-effectiveness
analysis does, and the case is available now.

## 6. What I want a second opinion on

1. **Whether one nameable ward is enough for Proof Two.** My read: report the
   aggregate result (permutation p = 0.001) as the finding, and Jakkur as a
   worked case validated against its own drainage spend. That is honest and it
   is a demonstration of method rather than a detector. If you want a list, the
   data does not support one at ward level.
2. **Whether the non-register restriction will survive a reviewer.** It is
   genuinely pre-specified in §12.5, but it is also the only thing that gets a
   ward over the FDR line, and that will attract attention. Worth deciding now
   how it is presented.
3. **The split-half instability (ρ = 0.035).** I report it as a warning. It
   could be read more harshly — as evidence that even the aggregate signal is
   not persistent. Ten quarters per half is thin, so I do not think it is
   decisive either way, but it is the weakest point in §23.
4. **Whether to attempt the 15 dateless wards.** Dates appear recoverable from
   the `brnumber` string by regex. It is maybe an hour, it would restore the
   Bommanahalli/South block, and those wards include Bilekahalli, Begur,
   Gottigere and Arakere — several of them active flood wards. I did not do it
   because the brief said feasibility check, not build.

## 7. Verification

57 tests pass (analysis only, no pipeline code). Database unchanged.

New: `data/reference/ward_relative_trends.csv` — per-ward Theil–Sen slopes and
Mann-Kendall p-values under all three nulls, plus first/last-4-quarter event and
complaint counts. `data/raw/work_orders/` (198 files, gitignored).

Method: 20 complete quarters 2020Q2 → 2025Q1. Standardised incidence ratio with
+0.5 smoothing. Theil–Sen slope, Mann-Kendall significance. Eligibility ≥15
strict event-days (103 wards). Permutation null 2,000 draws shuffling quarters
within ward. BH-FDR one-sided on the rising hypothesis.
