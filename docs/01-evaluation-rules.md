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

## Proof One — the ranking is dynamic

*If tonight's top 20 is the same 20 every night, this is a report, not a tool.*

- Baseline: static "20 historically worst" list — what an officer uses today.
- Measure precision@20 across held-out rain events.
- Measure Kendall's tau between consecutive events' rankings. Low correlation
  **plus** high precision means the model is reading the weather, not
  memorising the register.
- **Due Phase 3, before the mid-review**, so there is time to adapt if it fails.

## Proof Two — emerging detection finds real additions

- Mann-Kendall / CUSUM on per-location complaint rate normalised by rainfall.
- Validate: train through year *n*, check flagged sites show sustained
  elevation in *n+1*.
- Delhi upside if the RTI lands: predict which sites PWD *adds* to next year's
  list, using the municipality's own revisions as ground truth.

## Reporting bias

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
