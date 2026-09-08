# REPORT — the loader lands, and the effectiveness result does not survive

Task: NEXT.md "hazard categories, then the complaints loader". Completed
2026-09-08.

**The build worked: 237,157 complaints are in the database, idempotent, and the
reconciliation test passes exactly — the pipeline reproduces every published
figure to better than 1e-9.**

**But the added-variable plot you asked for broke the headline result. There is
no dose-response. Refitting on treated wards only gives −0.0064 (p = 0.833)
against the published −0.0240 (p = 0.0138). The effect was leverage from 7
untreated wards sitting at `log1p(0)` — a treated-versus-control contrast, using
exactly the seven wards §25.2 had already ruled out as a control group.**

**The project no longer has a positive intervention-effectiveness result.** The
allocation finding survives and is unaffected.

Profile §27. Retraction banners added to §25.4 and §25.8.

---

## 1. What was built

**`data/reference/hazard_categories.yaml`** — 9 waterlogging sub-categories
split `event` (3, the strict label) / `maintenance` (6), the Solid Waste
category with its 13 sub-categories, 4 explicit exclusions with reasons, the
9-value status map, and the work-order drainage patterns. Every entry carries
its row count so drift shows in a diff. Strings are byte-exact, including the
double space in `Storm  Water Drain(SWD)`.

I recorded the **exclusions** deliberately — `No water supply in public
toilet(s)`, `Lake water misused`, `Water quality`, `Debris Removal` — so nobody
re-litigates them. The work-order section is flagged as **different in kind**:
free text means patterns, not exact strings, and it says so.

**`app/ingestion/bbmp_complaints.py`** — driven entirely by the YAML.

```
237,157 complaints upserted of 766,648 read
  by hazard   : {'GARBAGE': 195153, 'WATERLOG': 42004}
  by severity : {'operational': 195153, 'maintenance': 33711, 'event': 8293}
  dropped     : 529,491 non-hazard, 0 null ward, 0 unresolved ward, 0 bad date
```

Exactly the YAML's expected totals. Idempotent — re-running leaves 237,157.
PyYAML added to `requirements.txt`.

## 2. The reconciliation test — passes, and found a design gap

`tests/test_reconciliation.py`, 9 assertions: same 110 wards, `ev_pre` and
`ev_post` identical, `pre` and `post` matching to **< 1e-9**, loader counts
matching the YAML, no complaint carrying a time component, window
2020-02-08 → 2025-06-19. **All pass.** The database and the paper agree.

**The gap it surfaced:** the index denominator is the ward's *total* complaints
across every category, but rule 7 forbids loading all 766,648 rows and the
loader keeps only the 237,157-row subset. **The database alone cannot rebuild
the index.**

I persisted the denominator as `data/reference/ward_period_totals.csv` — 4,356
ward-quarter rows, written by the same pass that reads the CSVs, version
controlled and diffable like the other reference artifacts. Its proper home is a
`ward_period_totals` table, which needs a migration, and Alembic still has no
baseline. **That is now a real dependency, not just tidiness.**

## 3. The added-variable plot, and what it did

You were right that it is the correct figure. It shows the relationship the raw
scatter hides:

| | r | p |
|---|---:|---:|
| Raw scatter, log spend vs Δ | −0.115 | 0.230 |
| **Added-variable (both residualised on controls)** | **−0.236** | **0.0130** |

Then I binned the residuals to describe the figure, and bin 1 sat at
x = −6.667 while bins 2–6 spanned −0.16 to +3.13. That gap is the 7 untreated
wards at `log1p(0)`.

| Specification | n | Coefficient | p |
|---|---:|---:|---:|
| **All wards (published §25.4)** | 110 | **−0.0240** | **0.0138** |
| **Treated wards only** | **103** | **−0.0064** | **0.833** |
| Spend > ₹1 M | 99 | −0.0174 | 0.614 |
| Spend per km², treated only | 103 | −0.0064 | 0.833 |
| Spend rank among treated | 103 | −0.0566 | 0.727 |
| Treated **indicator**, no dose | 110 | **−0.4497** | **0.0084** |

**Among wards that received drainage work, spend does not predict the outcome
at all.** And a bare treated/untreated indicator is *stronger* than the dose —
which is the signature of a two-cluster fit, not a gradient.

## 4. Why this is fatal rather than a caveat

§25.2 says, in its own words, that treated-versus-control is unavailable
because "the untreated wards are untreated *because BBMP judged they needed
nothing* — that is selection, not a control group."

The published result then rested on exactly that comparison. `log1p` disguised
it as a continuous dose and neither of us noticed.

The seven wards:

| Ward | pre | post | Δ | events |
|---|---:|---:|---:|---:|
| A.Narayanapura | 3.00 | 1.45 | **−1.55** | 35 |
| Hoodi | 2.15 | 1.30 | −0.85 | 121 |
| Domlur | 1.11 | 1.05 | −0.06 | 18 |
| J.P.Park | 0.60 | 1.37 | +0.77 | 20 |
| Gandhi Nagar | 0.78 | 1.69 | +0.91 | 43 |
| K.R.Market | 1.04 | 2.08 | +1.05 | 24 |
| Dharmarayaswamy Temple Ward | 1.06 | 2.55 | **+1.49** | 53 |

§26.3 already reported this group's mean as +0.251 with CI [−0.778, +1.280] —
not distinguishable from zero. A result resting on seven wards whose own mean is
insignificant, in a comparison the same document called invalid, is not a
result.

## 5. What survives

**Untouched — the allocation findings.** They are about how spend is
distributed, not about outcomes:

- Spend vs pre-period relative index: r = −0.083, p = 0.39.
- Spend vs ward area: ρ = +0.474. Spend vs absolute events: ρ = +0.274,
  collapsing to −0.050 (p = 0.603) once area is controlled.
- **BBMP allocates drainage spend by ward size, not by flooding need.**

That is now the strongest thing this output produced, and it is a finding about
institutional memory in a project about institutional memory.

**Survives as description only.** The Jakkur timeline is still correct — ₹840 M,
index 0.55 → 0.93 → 1.42, spend preceding the rise. It illustrates; it does not
identify an effect.

## 6. The rule I added

> **Before reporting a dose-response, refit on treated units only.** If the
> coefficient does not survive dropping the zero-dose group, it is a
> treated-versus-control contrast wearing a dose-response's clothes.

Neither the coefficient, its CI, the residualisation check, nor the quintile
table caught this. The added-variable plot caught it immediately. It is now the
standard figure for any regression this project reports.

## 7. What I want a second opinion on

1. **Whether to attempt a defensible effectiveness design at all.** Options as I
   see them: (a) accept that this output has an allocation finding and no
   outcome finding; (b) find within-ward timing variation — compare a ward's
   index before and after its own works, using ward fixed effects, which does
   not need a control group; (c) drop the output. **(b) is genuinely worth one
   session** and is a different identification strategy rather than a re-run,
   but it is analysis and you closed analysis. Your call whether it reopens.
2. **Whether the retraction convention is being applied consistently.** This is
   the third retraction (register contradiction, Q5, now this). I kept §25.4
   intact with a banner, per §25.7's convention, since it is a claim rather than
   an instruction. But §25.8 contained the sentence "this is the project's one
   positive quantitative result", which is closer to a framing instruction — I
   struck it through and pointed to §27.4. Say if you would rather it were left
   whole.
3. **The `ward_period_totals` table.** It is now blocking a clean
   database-only pipeline, so the Alembic baseline has moved from tidiness to
   dependency. I left it in the queue rather than promoting it, because the
   frontend can read the CSV. Confirm or promote.

## 8. Verification

**66 tests pass** (9 new in `test_reconciliation.py`). Database: `locations`
596, `complaints` **237,157**, `weather_observations` 1,309,896, `weather_daily`
54,579.

```
python -m app.ingestion.cli complaints --city Bengaluru   # idempotent
python -m app.ingestion.cli complaints --totals           # denominator only
python -m app.ingestion.cli status
```

New: `data/reference/hazard_categories.yaml`,
`data/reference/ward_period_totals.csv`, `app/ingestion/bbmp_complaints.py`,
`tests/test_reconciliation.py`. PyYAML pinned in `requirements.txt`.
