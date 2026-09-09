# UFMS — Build Plan (rev 2, decision-support framing)

> **HISTORICAL. Do not read the schedule or the volumes below as current.**
> Kept because it records what was planned and why, which is worth having beside
> what happened. Checked against the live system on 10 September 2026:
>
> | Planned here | Actually happened |
> |---|---|
> | P0 Sep 8–21, then P1 through P8 to Apr 2027 | **Phases 0–4 all landed in September 2026.** A progress evaluation on 16 Sep 2026 pulled everything forward. |
> | P3 Nov 10 – Dec 7: memory engine + Proof One | Proof One was **measured** in September and became a *ceiling* rather than a model. The memory engine and the M0–M3 ladder are still queued. |
> | P7 Feb 23 – Mar 1: deploy | Prepared and verified locally in September; not provisioned. `docs/04-deploy.md`. |
> | complaints ~600k after filtering | **237,157** |
> | weather_observations ~350k | **1,309,896** (two reanalyses, 23 cells) |
> | failure_memory ~30k, risk_predictions ~590k, daily_rankings ~590k | **all three are empty** — the memory engine is not built |
> | "about 2M rows, 400–600 MB" | **1,610,832 rows, ≈218 MB** |
> | Rainfall: ERA5 | **ECMWF-IFS** (~9 km) since profile §17; ERA5 cells 1–9 are kept for reference |
> | Hotspot register: ~210 areas, 58 highly prone | **398 points** loaded across three KML layers, unmerged |
>
> The current state is in `CLAUDE.md`; the work queue is in `NEXT.md`; every
> figure quoted anywhere is checked by `scripts/verify_documented_figures.py`.

Target: April 2027 submission, mid-review ~7 Dec 2026. Team 2–3. Zero budget.

## Phases

| Phase | Dates | Focus |
|---|---|---|
| P0 | Sep 8–21 | Foundation: schema, scaffold, CI. **DONE** |
| P1 | Sep 22 – Oct 12 | Ingest Bengaluru + Delhi (both are downloads) |
| P2 | Oct 13 – Nov 9 | Backend core: auth, RBAC, CRUD, logging |
| P3 | Nov 10 – Dec 7 | Memory engine + **Proof One** → mid-review demo |
| P4 | Dec 8 – Jan 11 | Frontend: Tonight's Priority List, Leaflet, Recharts |
| P5 | Jan 12 – Feb 8 | Emerging + effectiveness → **Proof Two**; results section |
| P6 | Feb 9–22 | Alerts + outcome loop closure |
| P7 | Feb 23 – Mar 1 | Deploy (Vercel + Render + Aiven) |
| P8 | Mar 2–22 | Testing, paper, report, viva deck |
| Buffer | Mar 23 – Apr 12 | 3 weeks |

Track split (3 people): A → P1/P3/P5 (data, memory, proofs); B → P2, supports
P6–P7; C → P4, supports P8.

## Data sources

| What | Source | Notes |
|---|---|---|
| Complaints | [BBMP Grievances, OpenCity](https://data.opencity.in/dataset/bbmp-grievances-data) | 6 yearly CSVs 2020–2025, ward level, public domain. ~127k records in 5½ months of 2025 alone. **Filter to waterlogging + solid waste at ingestion.** |
| Hotspot register | [Flooding Locations in Bengaluru Urban](https://data.opencity.in/dataset/flooding-locations-in-bengaluru-urban) | ~210 BBMP flood-prone areas, 58 highly prone. The triage candidate list. |
| Interventions | [BBMP Work Orders by Ward 2013–2022](https://data.opencity.in/dataset/bbmp-work-orders-by-ward-2013-2022) | Source for the effectiveness analysis |
| Rainfall | [Open-Meteo Archive API](https://open-meteo.com/en/docs/historical-weather-api) | ERA5, hourly, 1940→, free, no API key |
| Delhi hotspots | PWD / Traffic Police annual lists | 194 (2024) → 169 (2025). Demo city only. |
| Geography | OpenCity ward boundaries, OpenStreetMap, SRTM | Free |

## Zero-budget stack

Local MySQL via docker compose · **Aiven** free tier for hosted MySQL (1 GB,
no card, forever — Railway killed its free tier) · Render for the API (sleeps
when idle) · Vercel for the frontend · Brevo or Gmail SMTP for alerts ·
laptop for training (random forest on ~120k rows takes seconds — **do not pay
for GPU**) · GitHub Student Developer Pack covers the rest.

Real costs: RTI ₹10/application, report printing ₹500–1500, and publication
fees — ask whether a free Zenodo/arXiv DOI satisfies the requirement before
paying a pay-to-publish journal.

## Data volume (why MySQL is fine)

*These were the estimates. The measured figures are in the table at the top of
this file — the direction of the error is interesting: complaints came in at 40%
of the estimate and weather at nearly 4x, because the grid was tripled in
resolution after ERA5 turned out to resolve BBMP into three cells.*

complaints ~600k (after filtering) · weather_observations ~350k ·
failure_memory ~30k · risk_predictions ~590k · daily_rankings ~590k.
About 2M rows, 400–600 MB. MySQL handles hundreds of millions.

**Train from Parquet, not MySQL.** The database is the system of record; the
location-day panel is a derived artifact.

## Paper

Title: *Urban Failure Memory — A Decision Support System for Preventive
Municipal Maintenance Using Complaint-Derived Recurrence.*

Related-work home: decision support systems for flood risk management
(J. Hydroinformatics 2005 onward; GIS-based MCDM for flood control
prioritisation). DSS are evaluated on decision quality, so precision@k is the
field's own convention — you never defend an accuracy number.

Also cite: NYC 311 street-flooding studies (Agonafir et al. 2022) as closest
data-driven neighbours; PetaBencana.id as the deployed real-world comparator;
311 reporting-bias work (Annals of Applied Statistics 19(2), 2025; *Equity in
311 Reporting*, arXiv 1710.02452) for limitations.

Gap in one sentence: existing work is hydraulic-simulation-driven,
single-output, focused on risk mapping; UFMS is complaint-derived, operates on
a municipality's existing hotspot register, and produces three decision
outputs including intervention evaluation — which is essentially absent from
the literature.
