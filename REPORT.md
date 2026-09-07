# REPORT — per-ward recompute of §13 and §14

Task: NEXT.md "recompute §13 and §14 per-ward". Completed 2026-09-07.
Written for the reader who decides what happens next; assumes no access to the
conversation. All figures reproduced from committed code and data.

**Headline: the task's premise did not survive contact with the data. Per-ward
rainfall makes both figures slightly worse, not better, and §12.6's prediction
is now retired. The headline Proof One baseline is unchanged at
precision@20 = 13.6% against a 37.4% ceiling.**

---

## 1. What was built

| Artifact | State |
|---|---|
| `data/reference/ward_crosswalk.csv` | Rebuilt. 198 rows, new schema, all wards mapped |
| `app/ingestion/ward_crosswalk.py` | Rewritten for the new schema; adds haversine + `nearest_cell` |
| `app/ingestion/bbmp_wards.py` | New. Ward centroids + register hotspots into `locations` |
| `app/ingestion/cli.py` | New `wards` subcommand; `status` now reports `locations` |
| `tests/test_ward_crosswalk.py` | Rewritten, 30 tests. Suite total 46, all passing |
| `docs/02-data-profile.md` | New §16; §15 marked partly superseded; §12.6 retired |
| `data/raw/` (gitignored) | 5 new files downloaded from OpenCity |

Database state: `locations` = 596 rows (198 wards + 398 register points), every
row with a `cell_id`. Idempotent — re-running `wards` leaves 596.

## 2. Data sourced

From the OpenCity CKAN API, dataset `bbmp-ward-information`:

- `bbmp_ward_map_2015.kml` — **198 placemarks. This is the delimitation in
  force for the whole complaint period (2020-02 .. 2025-06)** and the one used.
- `bbmp_ward_map_2022.kml` — 243 placemarks. Not the right delimitation, but
  decisive for one hard case (§4 below), so kept.
- `bbmp_zone_boundaries_2022.kml`, `bbmp_ward_information.csv`,
  `bbmp_ward_area_road_length.csv` — cross-checks and ward area.

The 2015 file has no interior rings, 204 outer rings across 198 placemarks
(3 multi-ring wards). Centroids are area-weighted shoelace over lon/lat, which
is ample at city scale.

## 3. Crosswalk rebuild — before and after

| | Register-based (§15) | Boundary-based (§16) |
|---|---:|---:|
| Wards with a ward number | 102 | **198** |
| Complaint rows covered | 59.69% | **100%** |
| `exact` | 55 | 106 |
| `normalised` | 20 | 44 |
| `manual` | 27 | 48 |
| `unresolved` | 0 | **0** |

New columns: `bbmp_ward_no`, `bbmp_ward_name`, `bbmp_zone`, `centroid_lat`,
`centroid_lon`, `ward_area_sqkm`, `match_method`, `in_flood_register`,
`register_ward_name`, `notes`. The `not_in_register` match method is gone —
register membership is now a boolean column, which is what it always was
semantically. `match_method` is back to the spec's four values.

**Independent validation: all 102 register-derived ward numbers agree with the
boundary file. Zero disagreements.** That confirms the §15 hand decisions,
including the two contested ones (`Ulsoor`→90, `Kempapura Agrahara`→122). I
consider the §15 method vindicated.

Ward numbers now cover 1..198 exactly, each claimed once — asserted in the
build and pinned by `test_ward_numbers_cover_1_to_198_exactly`.

## 4. The two hard cases — and a correction to the task note

NEXT.md said:

> Register ward 65 is resolved. It is Kadumalleshwura, West Zone, sitting
> between Rajamahal (64) and Subrahmanyanagar (66) — i.e. it is the
> complaint-side `Kadu Malleshwar`.

**The geography is exactly right and confirmed** — boundary ward 64 is
`Rajamahal Guttahalli`, 65 is `Kadu Malleshwar Ward` (West), 66 is
`Subramanya Nagar`. **But the conclusion does not follow: there is no
complaint ward named `Kadu Malleshwar`.** That string is the *register* and
*boundary* spelling. The gap was always on the complaint side — some complaint
ward name had to be ward 65, and the note does not say which.

Matching all 198 complaint names against the boundary file left exactly two
unclaimed on each side:

- complaint `Someshwara` (11,376 rows) and `Subedarapalya` (2,038 rows)
- boundary ward 3 `Atturu` (Yelahanka) and ward 65 `Kadu Malleshwar Ward` (West)

Neither `Someshwara` nor `Subedarapalya` appears in the 198-ward file, the
register, or `bbmp_ward_information.csv`. Resolution:

**`Someshwara` → ward 3.** Found via the 243-ward delimitation. In
`bbmp_ward_map_2022.kml`, ward 3 is `Someshwara Ward` (centroid 13.1037,
77.5744) and ward 4 is `Atturu Layout` (13.0957, 77.5550) — both carved out of
the single 198-ward 3 `Atturu` (13.1028, 77.5600). The complaint feed is using
the newer locality name for part of the old ward. Consistent with volume: 8.8
sq km, fast-growing north Bengaluru, 11,376 complaints. **I regard this as
solid.**

**`Subedarapalya` → ward 65.** By elimination once Someshwara resolved.
Corroborated but not proved: Subedarpalya is a Malleshwaram-belt locality, and
ward 65's BBMP Division and Sub Division are both `Malleshwaram` (1.4 sq km,
West zone). No source I have contains a `Subedarapalya` ward to check against.
**Marked in the CSV as the file's lowest-confidence row. This is the one thing
I most want a second opinion on** — see §8.

Note the elimination argument is only valid because both lists have exactly 198
entries and 196 pair independently. It is not a fuzzy match; string distance
scores `Subedarapalya` against `Kadu Malleshwar` at essentially zero.

The task note's explanation of *why* string distance failed on ward 65 ("the
space in Kadu Malleshwar made Malleshwaram score higher") is right about the
mechanism but describes the register→complaint direction. In the
complaint→boundary direction the failure is more complete: the two names share
almost no characters, so no fuzzy threshold would ever have proposed the pair.
It is a stronger example for the methods section than the note suggests.

## 5. Cell assignment — the finding that matters

Each ward assigned the nearest of the 9 ERA5 cells by haversine on its polygon
centroid:

| Cell | Wards |
|---|---:|
| 5 (centre) | **176** |
| 6 | 8 |
| 8 | 7 |
| 4 | 4 |
| 2 | 3 |

**176 of 198 wards (89%) share one cell. Only 5 of 9 cells are used.**

The grid is 3×3 at 0.2°, ~22 km spacing. BBMP spans ~0.26° × 0.28°, about
29 × 30 km. The city is barely larger than one grid step, so nearly every ward
centroid is nearest the middle. On 36.1% of days every ward receives an
identical rainfall value. The five used cells do differ — mean daily
max-minus-min spread 2.94 mm — but only 22 wards are positioned to receive that
difference, and sitting at the city's edge is not the same as sitting where the
storm was.

This is a property of ERA5 (~25–31 km native), not of the grid choice. Adding
cells will not help; the reanalysis has no finer structure to give.

## 6. §13 recomputed — reporting lag

| Rainfall series | City-mean lift | Per-ward lift | Change |
|---|---:|---:|---:|
| **lag 0 (same day)** | 3.06 | **2.89** | −5.6% |
| lag 1 | 3.13 | 3.08 | −1.6% |
| lag 2 | 2.74 | 2.66 | −2.7% |
| lag 3 | 2.44 | 2.34 | −4.1% |
| max over prior 3 days | 3.43 | 3.48 | +1.7% |

Per-ward lag 0: 3,262 events on 111,924 wet ward-days (2.9145%) vs 2,783 on
275,958 dry (1.0085%).

**χ² on the two wet-day rates: p = 0.575.** Indistinguishable. Every §13
conclusion survives: lag 0 is the right alignment, lag 1 is noise, lags 2–3 are
worse, the 3-day window's edge is denominator-driven.

## 7. §14 recomputed — the static baseline

The static ranking uses prior event counts only, so per-ward rainfall cannot
change the ranking itself. What it can change is which wards are *candidates*
on a given night — the operationally meaningful version, since crews only go
where it is raining.

| Variant | Days | precision@20 | Ceiling | % of ceiling |
|---|---:|---:|---:|---:|
| (A) city-mean rain days, all 198 ranked | 138 | **13.55%** | 37.36% | 36.3% |
| (A′) the 123 of those with ≥20 wet wards | 123 | 13.90% | 37.32% | 37.2% |
| (B) same 123 days, ranking only wet wards | 123 | **13.01%** | 35.45% | 36.7% |

Like-for-like (A′ vs B), restricting to wet wards **lowers precision@20 by
6.4%**.

Why: on a typical rain day **173 of 198 wards are already "wet"** at 2.5 mm,
because 89% read the same central cell. The restriction removes only ~25 wards,
and some of those had events — the ward flooded while its inherited cell read
dry. It costs more in lost true positives than it gains in narrowed candidates.

**Headline unchanged: precision@20 = 13.6%, ceiling 37.4%, random 4.7%.**

## 8. What I want a second opinion on

1. **`Subedarapalya` → ward 65.** The one elimination-derived row. 2,038
   complaint rows, 0.27% of the dataset, and it is not in the §14 top-20 — so
   the blast radius is small — but it is the weakest link in the artifact. A
   BBMP ward-65 street list or the 198-ward PDF would settle it. The task note
   cited `https://dl.bbmpgov.in/download/map/198-wards.pdf`; I did not fetch it
   (the OpenCity CSV gave the same ward-name/number table and agreed with the
   KML, so it added nothing at the time — but it may list localities, which
   would settle this).
2. **Whether to retire §12.6 as firmly as I have.** I marked it RETIRED with a
   strikethrough and told the reader to quote city-mean figures without the
   apology. That is a strong claim built on one comparison. The counter-argument
   is that the per-ward test was *underpowered by construction* — 89% shared
   cell means it barely tested the hypothesis. It may be truer to say "untested,
   and untestable with ERA5" than "wrong". I lean to my wording because the
   practical instruction is identical either way, but it is a judgement call.
3. **Whether §16.6's claim about M1/M2 is too strong.** I wrote that ERA5-only
   models "cannot discriminate between wards on a given night — only between
   nights". That follows from 89% sharing a cell, but M2 includes terrain, and
   terrain does vary per ward. The claim is about M1 strictly and about the
   *weather component* of M2. Worth tightening if it goes into the paper.
4. **Queue ordering.** I promoted the complaints loader as instructed, but it
   depends on `hazard_categories.yaml`, which is the item below it. Flagged in
   NEXT.md rather than reordered unilaterally.

## 9. Things a future reader should not have to rediscover

- `bbmp_low_lying_areas.kml` stores the literal string `nan,nan` as coordinates
  for placemark 83 (`KARAMCHAND LAYOUT NEAR KARIYANNA PALYA`). `float()`
  succeeds on it, so a `None` check misses it and MySQL then rejects the insert.
  Handled with an explicit `math.isnan` guard; the row is skipped and counted
  as rejected in `ingestion_runs`.
- `bbmp_ward_area_road_length.csv` has a trailing `Total` row that breaks
  `int()` on the ward number.
- The 2015 boundary file's `ZONE` field spells one zone two ways
  (`Rajarajeshwari Nagar` and `Rajarajeswari Nagar`). Do not group on it
  without normalising.
- The boundary file has a typo: ward 82 is `Garudachar Playa`, for *Palya*.
- The register's `ZONE` is separately unreliable — ward 73 appears twice under
  two different zones (§15.5). Use `WARDNO`.

## 10. Verification

```
46 tests pass (30 in test_ward_crosswalk.py, rewritten for the new schema)
python -m app.ingestion.cli wards --city Bengaluru   # idempotent, 596 rows
python -m app.ingestion.cli status
```

`locations` 596 · `weather_observations` 512,568 · `weather_daily` 21,357.
Ward-number coverage, centroid presence and bounds, centroid distinctness,
no-double-claim, and the five pinned hand decisions are all asserted in tests
rather than checked by eye.
