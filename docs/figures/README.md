# Figures

Rendered from the running system against the loaded database — nothing here is
mocked, redrawn or illustrative. The number in a figure is the number the API
serves, so a figure and the text can only disagree if the data changed.

Regenerate:

```bash
cd ../../ufms-backend && uvicorn app.main:app          # :8000
cd ../ufms-frontend    && npm run dev                  # :5173
node scripts/paper-figures.mjs                         # writes back into here
```

Deterministic: the derived tables are built from fixed windows, so a re-run
produces the same figures until the underlying data changes. 2× scale, so they
survive a two-column layout.

## The four that carry a claim

| File | Shows | The numbers in it |
|---|---|---|
| `fig-precision-scale.png` | The triage result, as a position on a scale | precision@20 **14.08%**, chance floor **4.79%**, oracle ceiling **37.72%** — 37% of achievable, 2.9× chance. 136 held-out rain days, 1,289 events. |
| `fig-jakkur-index.png` | The case study: the 2nd-highest drainage spender getting worse | Jakkur, ₹494 M of drainage work 2021–22. Relative index **0.22 (2020Q2) → 1.64 (2025Q1)**, mean 1.09, above the city norm in 10 of 20 quarters. The spend came first (§25.6). |
| `fig-allocation-scatter.png` | The allocation finding, as a pair | Spend vs ward area **ρ = +0.474, p < 0.0001**; spend vs relative flooding need **ρ = +0.082, p = 0.392**. Same spend on both x-axes. No fitted line: the dose-response is retracted. |
| `fig-level-persistence.png` | What the emerging detector actually finds | Ten flagged wards, first half → second half. Mean **1.42 → 1.77** against **1.16** for all eligible wards (Mann-Whitney U, one-sided, p = 0.00014); **10 of 10** finish above the norm, but they do not exceed their own first half (Wilcoxon signed-rank, p = 0.116). |

## Context

| File | Shows |
|---|---|
| `fig-ward-choropleth.png` | All 198 wards by relative index, 2025Q1. Diverging about 1.00; classes are multiplicative (×1.41) because the index is a ratio. |
| `screen-watchlist.png` | Screen 2 entire — the list with its measured context. |
| `screen-index.png` | Screen 1 entire — series, map and the inputs table. |
| `screen-emerging.png` | Screen 3 entire — ranking, evidence, and the "no ground truth" banner. |
| `screen-allocation.png` | Screen 4 entire — the retraction, both panels, correlations, per-ward table. |

## Two notes for whoever writes the caption

**`fig-precision-scale.png` is the argument, not a decoration.** Its whole point
is that 14.08% is unreadable alone. A caption that quotes the figure without the
floor and the ceiling re-creates exactly the problem the figure was built to
solve.

**`fig-allocation-scatter.png` has no trend line and must not be given one.**
The dose-response of the change in index on spend does not survive dropping the
seven zero-dose wards (−0.0240, p = 0.0138 → −0.0064, p = 0.833), and a line
through a scatter is read as an effect estimate whatever the caption says. The
two panels are a rank-correlation contrast, and the contrast is the finding.
