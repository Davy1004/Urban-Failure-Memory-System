# REPORT — is reporting growth about to invalidate Proof Two?

Task: NEXT.md "is reporting growth about to invalidate Proof Two?". Completed
2026-09-08. Written for the reader who decides what happens next; assumes no
access to the conversation.

**Yes, and worse than the brief anticipated. On raw event counts 7 wards show a
significant rising trend. After normalising by each ward's own complaint volume,
that number is 0 — under any of three denominators — while 10 wards show
significant declines. The naive emerging-hotspot test would have been entirely
false positives.**

**And the correction does not rescue it. After normalising there is no emerging
signal at ward level at all: zero wards rise at p < 0.10, closest p = 0.139, in
a test that finds ten significant declines. Proof Two has no positive result to
report.**

That is the headline and it needs a project-level decision, not a doc edit.
Full write-up: profile §22. Options in §22.6 and in §6 below.

---

## 1. Growth is not uniform (your question 1)

Citywide, all categories: 103,504 (2021) → 207,016 (2024) = **2.00×**. Only
complete years used; 2020 starts 8 Feb and 2025 ends 19 Jun.

Per-ward growth ratios, n = 198:

| p0 | p10 | p25 | p50 | p75 | p90 | p100 |
|---:|---:|---:|---:|---:|---:|---:|
| 0.87× | 1.42× | 1.66× | 2.00× | 2.44× | 3.00× | 4.81× |

Mean 2.11×, sd 0.65, **p90/p10 = 2.12×**. Two wards shrank; twenty more than
tripled. Fastest: Siddapura 4.81×, Doddanekkundi 4.32×, Banashankari Temple Ward
3.67×. Slowest: Moodalapalya 0.87×, Nayandanahalli 0.89×.

**Answer: wards diverge widely.** This is not a uniform multiplier that cancels
out of a per-ward trend test. It is fatal to a naive one, which §4 confirms
directly.

## 2. It does not track socioeconomics (your question 2)

I found better data than expected: the OpenCity **BBMP 2014 delimitation CSV**
carries total population, male/female, **SC population and ST population** per
ward. SC+ST share is a meaningful marginalisation proxy in this context. Saved
as `data/reference/ward_socioeconomic.csv` (198 rows, all matched).

Spearman ρ against the 2021→2024 growth ratio:

| Proxy | ρ | p |
|---|---:|---:|
| Total population | −0.109 | 0.125 |
| Ward area | −0.021 | 0.771 |
| Population density | 0.014 | 0.839 |
| **SC + ST population share** | **−0.057** | **0.423** |
| Centroid elevation | 0.055 | 0.439 |
| **Elevation range** | **−0.231** | **0.001** |
| **Complaints per 1,000 residents, 2021** | **−0.147** | **0.039** |

By zone: periphery 1.96× vs core 2.01×, Mann-Whitney p = 0.708 — **no
core/periphery effect**, which surprised me.

**Answer: the growth is idiosyncratic, not an equity gradient.** The
marginalisation proxy is flat. Two weak real effects: flatter wards grew faster
(plausibly new peripheral development), and already-loud wards grew less
(saturation).

This is genuinely good news and worth saying in the paper: the reporting-growth
confound is a **noise** problem, not a **bias** problem, so correcting for it
does not itself introduce a social distortion. It does not weaken the
cross-sectional reporting-propensity concern — only the claim about growth.

## 3. The normalisation (your question 3)

Strict event-days as a share of the ward's own complaints, per quarter, 20
complete quarters (2020Q2 → 2025Q1).

Citywide:

| Denominator | First 4 quarters | Last 4 quarters |
|---|---:|---:|
| All complaints | 0.854% | 0.667% |
| Categories present in all 6 years | 0.854% | 0.680% |
| Solid-waste complaints only | 3.297% | 2.447% |

**The share is flat-to-declining while volume doubles.** That is the signature.

I checked the obvious objection — BBMP added whole categories mid-window (§9.4),
which would inflate the denominator for unrelated reasons. It does not bite: the
eleven mid-window categories are **0.7%** of rows in this window, and the three
denominators agree at ρ = 0.995 (all vs stable) and 0.85 (vs solid-waste-only).

I also moved from a two-point annual ratio to **Theil–Sen slopes with
Mann-Kendall on 20 quarterly points**. A two-point ratio is too fragile to
support a ranking claim, and the choice matters: annual gives Spearman 0.923
between raw and normalised rankings, quarterly gives **0.394**. The fragile
version would have understated the problem substantially.

## 4. Raw vs normalised (your question 4)

103 wards with ≥15 strict event-days across the window.

| Series | Significantly rising | Significantly declining |
|---|---:|---:|
| **Raw event count** | **7** | 3 |
| **Normalised (all complaints)** | **0** | 10 |
| Normalised (stable categories) | 0 | 9 |
| Normalised (solid-waste denominator) | 0 | 10 |

Top-20 overlap: **11/20**. Spearman on slopes: **0.394**.

**Drop out when normalised** — the apparent rise was volume:

| Ward | Raw rank | Norm rank | Volume growth |
|---|---:|---:|---:|
| Chikpete | 6 | 76 | 3.30× |
| **Bellandur** | **7** | 91 | 2.60× |
| Gandhi Nagar | 8 | 32 | 2.12× |
| Kuvempu Nagar | 9 | 29 | 3.25× |
| **Varthur** | **11** | 85 | 2.51× |
| Hemmigepura | 12 | 59 | 2.98× |
| Kodigehalli | 16 | 71 | 3.69× |
| Ejipura | 19 | 97 | 1.84× |
| Aramane Nagar | 20 | 39 | 1.85× |

**Enter when normalised** — real relative rise, masked by flat volume:
Puttenahalli (7 / raw 87), Yelahanka old Satellite Town (8 / 89), K.R.Market
(12 / 63), Chamrajpet (13 / 32), Benniganahalli (14 / 36), Basavanagudi
(15 / 39), Hebbal (16 / 43), BTM Layout (19 / 31), Cottonpet (20 / 23).

Bellandur and Varthur are the two most notorious flooding wards in Bengaluru and
both sit in the raw top 11. On a raw test they would be reported as *newly
emerging*, which is obviously wrong and is the cleanest illustration of the
problem for the paper.

## 5. The four register-absent wards (your named check)

Your caution was right.

| Ward | Raw rank | Norm rank | Volume growth | Norm slope | p |
|---|---:|---:|---:|---:|---:|
| **Jakkur** | **1** | 4 | 3.11× | +0.00026 | 0.183 |
| Basavanapura | 37 | 60 | 1.82× | −0.00008 | 0.586 |
| Someshwara | 81 | 84 | 2.18× | −0.00048 | 0.074 |
| **Hoodi** | 54 | 101 | **3.06×** | **−0.00099** | **0.007** |

**Jakkur ranks first in the city on raw event growth**, and is exactly the
rapid-development corridor you predicted — 3.11× volume growth. It survives
normalisation better than the others at 4th, but p = 0.183.

**Hoodi is significantly declining** in normalised share (p = 0.007) despite
3.06× volume growth. On the raw test it would have looked like rising hazard.

This forces a distinction §21 ran together and I should have caught then:
*absent from the register with high total events* means **the register is out of
date**; *rising share* means **getting worse**. Different claims, different
tests. For these four only the first is supported.

## 6. The part that needs your decision

**After correct normalisation there is no emerging signal at ward level.** Zero
wards rising at p < 0.10 against ten declining, and the test demonstrably has
power.

The most likely cause is granularity. A ward averages 3.7 km² and thousands of
complaints a year; an emerging hotspot is a junction contributing perhaps a
dozen. Ward aggregation dilutes exactly what Proof Two is looking for — and the
complaint data carries no sub-ward geography (§8), so location-level detection
is not possible with this source. Same wall §19 hit from the other direction.

**Both proofs are now negative-shaped.** Proof One is a measured ceiling; Proof
Two is a measured confound. Three options, in §22.6:

1. **Reframe Proof Two as a methodological result too.** "Naive trend detection
   on civic-complaint counts yields seven spurious emerging hotspots over five
   years, every one explained by reporting growth; after normalisation none
   survives." Real, citable, honest — and not a working detector.
2. **Move the positive contribution to intervention effectiveness.** It is the
   third Learn output and has an **independent data source** — BBMP ward work
   orders 2013–2022, already in `docs/00-build-plan.md` and never yet touched.
   It does not depend on detecting a trend in complaint counts.
3. **Acquire sub-ward geography.** Nothing in current sources has it. New data
   acquisition, not analysis.

**My read: option 2, with option 1 as the write-up of Proof Two.** The ten
significant *declines* point the same way — waterlogging is becoming a smaller
share of BBMP's complaint mix, which is consistent with drainage works actually
working. That is an intervention-effectiveness finding sitting in plain sight,
and it would give the project a positive result that neither proof can currently
supply. It is also the only one of the three outputs with an independent data
source, which matters a great deal now that two outputs have turned negative.

**But this is a project-level call.** It changes what the mid-review demos and
what the paper claims, and it should not be made inside a profile document.

## 7. What I want a second opinion on

1. **Whether to go to the work-orders data next.** It is the untested third
   output and now carries the project. It is also the one dataset in the build
   plan nobody has looked at — it could have its own fatal flaw, and finding
   that out in December would be much worse than finding it out now. I would
   promote it above the complaints loader.
2. **Whether "no emerging signal at ward level" is a finding or a null.** I have
   written it as a finding, because the test has power and the confound
   explanation is specific. An examiner could reasonably call it an
   underpowered null on a 5-year window. The ten significant declines are the
   defence; I would like a second view on whether that defence holds.
3. **Whether the declines are real or another artefact.** Ten wards declining in
   normalised share is currently interpreted as "possibly drainage works". It
   could equally be that the *other* complaint categories grew faster for
   channel reasons. I did not test that and it needs testing before anyone
   claims improvement.
4. **The housekeeping bundle is now duplicated in the queue** as items 0 and 1
   (you restored it while my copy was already there). Cosmetic, but I have
   deduplicated it in this pass.

## 8. Verification

57 tests pass (unchanged — analysis, not pipeline code). Database unchanged.

New committed artifacts:
- `data/reference/ward_socioeconomic.csv` — 198 wards, population, SC/ST counts,
  density, area, assembly constituency, complaints per 1k, growth ratio.
- `data/reference/ward_growth_trends.csv` — per-ward Theil–Sen slopes and
  Mann-Kendall p-values for raw event count, normalised share, and volume.
- `data/raw/bbmp_ward_delimitation_2014.csv` and `bbmp_ward_reservation_2015.csv`
  (gitignored) — sources for the above.

Method: complete quarters only (2020Q2 → 2025Q1) to avoid the partial first and
last years. Theil–Sen slope with Mann-Kendall significance, 20 points per ward,
minimum 15 strict event-days for eligibility (103 of 198 wards). Growth ratios
use complete calendar years 2021 and 2024 with +1 smoothing.
