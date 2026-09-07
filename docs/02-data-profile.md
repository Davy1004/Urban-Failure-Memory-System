# UFMS — raw data profile

Profile of the BBMP source files in `data/raw/`. **No parser has been written
yet** — this document exists so that `app/ingestion/bbmp_complaints.py` is
written against what the files actually contain rather than against a guess,
per the standing instruction in `CLAUDE.md`.

Generated 7 Sep 2026 from the files as downloaded from
[OpenCity](https://data.opencity.in/). The raw files are gitignored
(`data/raw/`); only this profile is committed.

> **Read §8–§10 before writing the loader.** Five findings there change the
> design:
>
> 1. The timestamps have lost their AM/PM marker — time of day is unusable (§6).
> 2. 84% of the waterlogging signal sits under `Road Maintenance(Engg)`, not
>    under the storm-water-drain category (§10.1).
> 3. The complaints and the hotspot register cannot be joined on ward name
>    as-is — only 55 of 103 names match (§8.3).
> 4. `Category` and `Grievance Status` are not stable vocabularies across
>    years; two statuses were silently retired (§9.4, §9.5).
> 5. Absence is encoded as the literal string `null`, which pandas does not
>    treat as NA by default (§4).
>
> **§12 adds a sixth, measured against real rainfall:** two-thirds of the
> "waterlogging" complaints are routine drain maintenance that barely responds
> to rain (lift 1.3×). Filtering them out changes the ward-day base rate from
> 7.99% to 1.56% and the rain lift from 1.4× to 3.1×. The event label and the
> maintenance label must be modelled separately.
>
> **§13–§14 add the numbers Proof One is scored against.** There is no
> reporting lag worth modelling (§13). The static "20 historically worst wards"
> baseline scores **precision@20 = 13.6% on held-out rain days, against an
> oracle ceiling of 37.4%** and a 4.7% random baseline (§14.3). Re-ranking that
> list on more history does not improve it, so the remaining headroom belongs
> to weather and location features — which is the case for M3, measured rather
> than asserted.
>
> **§15–§18 close the ward join and settle the rainfall-resolution question.**
> All 198 complaint ward names map to a BBMP ward number with a polygon
> centroid (§16.1). The pipeline now runs on **ECMWF-IFS at ~9 km, which
> resolves BBMP into 14 cells** instead of ERA5's 3 (§17.1) — and per-ward
> rainfall *still* changes nothing (χ², p = 0.877). Tripling the resolution
> moves no figure, so the limit is not rainfall resolution.
>
> **§17.4 and §19 are the two results that decide Phase 3.** A weather-only
> ranker scores **5.63%** against a **4.80%** random baseline, while memory
> alone reaches **14.08%** and the ceiling is **37.72%** — weather alone ranks
> at chance (§17.4).
>
> And the 23.6-point gap between memory and the ceiling **is not reachable**
> (§19). A ward-level ranking fitted with perfect foresight of the test period
> gets 15.66%, so **only 1.6 points — 6.7% — of the headroom is ward-level at
> all**; the other 93.3% is within-ward temporal variation that nothing
> observable predicts. Terrain, elevation and the prescribed memory-weather
> interaction features were all built and tested; every one is worse than
> prior event count alone. **Read §19.7 before planning Phase 3, and §19.4
> before trusting any AUC.**

---

## 1. File inventory

| File | Source dataset | Format | Size | Records |
|---|---|---|---:|---:|
| `bbmp_grievances_2020.csv` | BBMP Grievances | CSV | 12.4 MB | 91,620 |
| `bbmp_grievances_2021.csv` | BBMP Grievances | CSV | 13.7 MB | 103,504 |
| `bbmp_grievances_2022.csv` | BBMP Grievances | CSV | 15.3 MB | 118,394 |
| `bbmp_grievances_2023.csv` | BBMP Grievances | CSV | 15.2 MB | 119,140 |
| `bbmp_grievances_2024.csv` | BBMP Grievances | CSV | 26.8 MB | 207,016 |
| `bbmp_grievances_2025.csv` | BBMP Grievances | CSV | 17.4 MB | 126,974 |
| `flood_vulnerable_map.kml` | Flooding Locations | KML | 103.7 KB | 200 |
| `bbmp_low_lying_areas.kml` | Flooding Locations | KML | 39.9 KB | 129 |
| `flood_prone_locations.kml` | Flooding Locations | KML | 21.8 KB | 70 |

**766,648 complaint rows** across six years (~101 MB of CSV), and **399
flood-location placemarks** across three KML layers.

The flood-prone dataset turned out to be **KML, not CSV** — three separate
point layers, described in §8. All nine files are valid UTF-8 with no BOM. The
CSVs are CRLF-terminated, comma-delimited, `"`-quoted, with no escape
character.

---

## 2. Complaint CSV schema

**All six CSVs share one identical header, byte for byte:**

```
Complaint ID,Category,Sub Category,Grievance Date,Ward Name,Grievance Status,Staff Remarks,Staff Name
```

No column was renamed, added, dropped, or reordered across 2020–2025. This is
the one place the dataset is better behaved than expected.

Everything arrives as text — there is no type information in the file. The
"target dtype" column is what the loader should impose, not what pandas infers.

| # | Column | Read as | Target dtype | Role |
|---:|---|---|---|---|
| 1 | `Complaint ID` | string | `int64` / `BIGINT` | Primary key — globally unique, see §7 |
| 2 | `Category` | string | category, 32 levels | Owning department. Coarse; **not** the failure type |
| 3 | `Sub Category` | string | category, ~200 levels | **The actual waterlogging signal** — see §10 |
| 4 | `Grievance Date` | string | **`DATE`, not `DATETIME`** | Time component is corrupt — see §6 |
| 5 | `Ward Name` | string | category, 199 levels | Name only, no ward number — see §5 |
| 6 | `Grievance Status` | string | category, 9 levels | Lifecycle state |
| 7 | `Staff Remarks` | string | `TEXT` | Free text, unnormalised, contains newlines |
| 8 | `Staff Name` | string | `TEXT` | `Name/Designation`, unnormalised |

There is **no complaint description or citizen-supplied text field.**
`Staff Remarks` is written by the handling officer after the fact, not by the
complainant, so it cannot be mined for what the citizen actually reported.

---

## 3. Sample rows

**`bbmp_grievances_2020.csv` — first three rows**

| Complaint ID | Category | Sub Category | Grievance Date | Ward Name | Grievance Status | Staff Remarks | Staff Name |
|---|---|---|---|---|---|---|---|
| 20096407 | Road Maintenance(Engg) | Road cutting | 2020-12-31 11:33:00.000000000 | Bagalagunte | Closed | After tender,it will be attended. | Ranganath/AEE |
| 20096406 | Electrical | Street Light Not Working | 2020-12-31 11:30:00.000000000 | Subedarapalya | Closed | Attended | Suresh/AEE |
| 20096405 | Electrical | Street Light Not Working | 2020-12-31 11:28:00.000000000 | Agrahara Dasarahalli | Closed | Attended | Suresh/AEE |

**`bbmp_grievances_2022.csv` — first three rows**

| Complaint ID | Category | Sub Category | Grievance Date | Ward Name | Grievance Status | Staff Remarks | Staff Name |
|---|---|---|---|---|---|---|---|
| 20318322 | Solid Waste (Garbage) Related | Dead animal(s) | 2022-12-31 05:43:00.000000000 | Agrahara Dasarahalli | Closed | Problem solved | Ranganath/JHI |
| 20318316 | Electrical | Street Light Not Working | 2022-12-31 11:46:00.000000000 | Kempapura Agrahara | Closed | Attended | Umesh/AEE |
| 20318315 | Electrical | Street Light Not Working | 2022-12-31 11:33:00.000000000 | Ullalu | Closed | ATTENDED | Gavi Siddiah/AEE |

**`bbmp_grievances_2025.csv` — first three rows**

| Complaint ID | Category | Sub Category | Grievance Date | Ward Name | Grievance Status | Staff Remarks | Staff Name |
|---|---|---|---|---|---|---|---|
| 20771690 | Electrical | Street Light Not Working | 2025-06-19 10:39:00.000000000 | Jagajeevanram Nagar | Registered | 1st Assignment Based on Ward Mapping | syed zameer/JE |
| 20771689 | Electrical | Street Light Not Working | 2025-06-19 10:36:00.000000000 | Kammanahalli | Registered | 1st Assignment Based on Ward Mapping | Vinay Kumar/AE |
| 20771688 | Solid Waste (Garbage) Related | Garbage dump | 2025-06-19 10:35:00.000000000 | Banaswadi | Registered | 1st Assignment Based on Ward Mapping | Marshal Ward No 27/Marshal |

Note `Closed` / `ATTENDED` casing drift in `Staff Remarks`, and that 2025's
head rows are all `Registered` rather than `Closed` — the tail of the extract
is unprocessed backlog, not a data error.

---

## 4. Null counts per column

**There is not a single true null in any of the six files.** Every cell in
every column of all 766,648 rows is populated.

| Column | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| `Complaint ID` | 0 | 0 | 0 | 0 | 0 | 0 |
| `Category` | 0 | 0 | 0 | 0 | 0 | 0 |
| `Sub Category` | 0 | 0 | 0 | 0 | 0 | 0 |
| `Grievance Date` | 0 | 0 | 0 | 0 | 0 | 0 |
| `Ward Name` | 0 | 0 | 0 | 0 | 0 | 0 |
| `Grievance Status` | 0 | 0 | 0 | 0 | 0 | 0 |
| `Staff Remarks` | 0 | 0 | 0 | 0 | 0 | 0 |
| `Staff Name` | 0 | 0 | 0 | 0 | 0 | 0 |

That clean sheet is misleading. **Absence is encoded as sentinel strings:**

| Sentinel | Column | Total | Years |
|---|---|---:|---|
| `null` (literal 4-char string) | `Grievance Status` | 74 | 2020 (3), 2021 (17), 2025 (54) |
| `null` (literal 4-char string) | `Staff Remarks` | 54 | 2025 (54) |
| `null` (literal 4-char string) | `Staff Name` | 54 | 2025 (54) |
| `NON Ward` | `Ward Name` | 2 | 2025 (2) |

`null` is **not** in pandas' default NA list, so it survives today as an
ordinary string and would be loaded as the literal text `"null"`. The loader
must pass `na_values=["null", "NON Ward"]` explicitly.

The two `NON Ward` rows are both `E khata / Khata services` complaints — an
administrative category with no physical location, so they are correctly
dropped by the waterlogging/solid-waste filter anyway.

---

## 5. Ward identifier

**Name only. There is no ward number anywhere in the complaint CSVs.** No
column holds a numeric ward code, and no ward name embeds a digit.

| Year | Distinct wards |
|---|---:|
| 2020 | 198 |
| 2021 | 198 |
| 2022 | 198 |
| 2023 | 198 |
| 2024 | 198 |
| 2025 | 199 |
| **union** | **199** |

198 wards in every year, matching BBMP's 198-ward structure. The 199th value
is the `NON Ward` sentinel, present only in 2025.

The ward vocabulary is otherwise **perfectly stable**: not one ward was added,
removed, or respelled across the six years. Within the complaint dataset,
`Ward Name` is a reliable join key.

Across datasets it is not — see §8.

---

## 6. Date column

`Grievance Date` is the only temporal column. One format, in 100% of all
766,648 rows, with zero unparseable values:

```
%Y-%m-%d %H:%M:%S.%f      e.g.   2022-12-31 05:43:00.000000000
```

Nine fractional-second digits, always zero. Seconds always `00`. No row is
filed under the wrong year's file.

| File | Min | Max | Parsed | Unparseable |
|---|---|---|---:|---:|
| `bbmp_grievances_2020.csv` | 2020-02-08 01:01 | 2020-12-31 12:57 | 91,620 | 0 |
| `bbmp_grievances_2021.csv` | 2021-01-01 01:04 | 2021-12-31 12:58 | 103,504 | 0 |
| `bbmp_grievances_2022.csv` | 2022-01-01 01:07 | 2022-12-31 12:59 | 118,394 | 0 |
| `bbmp_grievances_2023.csv` | 2023-01-01 01:18 | 2023-12-31 12:03 | 119,140 | 0 |
| `bbmp_grievances_2024.csv` | 2024-01-01 01:00 | 2024-12-31 12:59 | 207,016 | 0 |
| `bbmp_grievances_2025.csv` | 2025-01-01 01:00 | 2025-06-19 12:59 | 126,974 | 0 |

**Overall coverage: 2020-02-08 → 2025-06-19.** Two gaps at the edges:

- **2020 begins 8 February.** The first five and a half weeks of 2020 are
  absent from the source, not lost in download.
- **2025 ends 19 June**, the extract date. 2025 is a partial year and must
  never be compared to a full year without normalising by days elapsed.

### The timestamps are a 12-hour clock with AM/PM stripped

Hour-of-day across all 766,648 rows:

| Hour | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Rows | 48,328 | 37,408 | 38,521 | 39,711 | 43,790 | 67,066 | 89,357 | 87,392 | 88,577 | 89,291 | 77,485 | 59,722 |

**No row has hour 00, and no row has hour 13–23.** A real 24-hour distribution
over three-quarters of a million municipal complaints cannot avoid every
afternoon hour. The source system stored a 12-hour clock and the AM/PM marker
was dropped on export.

Consequences:

- **Time of day is unrecoverable.** A complaint stamped `05:43` is either
  05:43 or 17:43, and nothing in the file distinguishes them. Never derive an
  hour-of-day feature, a response-time, or a diurnal pattern from this column.
- **Parse to `DATE`, not `DATETIME`.** The date part is sound; the time part
  is noise that would look like signal.
- **Daily aggregation is unaffected**, which is what the memory engine needs.
  This costs the project nothing it was going to use — but only if the loader
  truncates deliberately rather than carrying a plausible-looking wrong time
  into `complaints.created_at`.

---

## 7. Deduplication key

**Yes — `Complaint ID` is a sound deduplication key, and stronger than needed.**

| Property | Result |
|---|---|
| Purely numeric | Yes, all 766,648 values |
| Unique *within* each file | Yes, all six |
| Unique *across* all six files | **Yes — 766,648 distinct over 766,648 rows, zero collisions** |
| Value range | 20,004,260 … 20,771,690 |
| Range width vs row count | 767,430 vs 766,648 — 782 gaps |

The ID is a **single global sequence allocated monotonically across all six
years**, not a per-year counter. So:

- The six files can be concatenated without a composite key.
- `Complaint ID` alone is safe as the natural key for
  `INSERT ... ON DUPLICATE KEY UPDATE` via the existing `upsert_chunk`.
- Re-downloading and reloading any year cannot create duplicates.
- Because IDs are issued in time order, an ID is also a coarse proxy for
  filing order — useful as a tiebreak, not as a timestamp.

The 782 gaps are consistent with complaints deleted at source or withheld from
the published extract.

---

## 8. Latitude / longitude, and the flood-location KMLs

**The complaint CSVs contain no coordinates of any kind** — no lat/lon, no
easting/northing, no address, no landmark, no pincode. The finest spatial
resolution available in the complaint data is the **ward**, and only by name.

The KML files do carry coordinates. That asymmetry defines the whole join
problem:

```
complaints ──(ward NAME, no coords)──> ??? <──(ward NAME + NUMBER + lat/lon)── hotspot register
```

### 8.1 The three KML layers

All three are OGC KML 2.2, `Point` geometry only — no polygons, no linestrings,
no `<description>` blocks. Coordinates are `lon,lat` (KML order), WGS84,
and all fall inside the Bengaluru bounding box.

**`flood_vulnerable_map.kml` — 200 placemarks. This is the hotspot register.**

| Field | Distinct | Missing | Notes |
|---|---:|---:|---|
| `OBJECTID` | 200 | 0 | 1…200, row identity only |
| `WARD_NAME` | 103 | 1 | Ward name |
| `WARDNO` | 103 | 0 | **Ward number, 1–198** |
| `LocationName` | 200 | 0 | Free-text place description, all distinct |
| `KGISFVLID` | 200 | 0 | Karnataka GIS flood-vulnerable-location id |
| `ZONE` | 8 | 0 | BBMP zone |
| `lat` / `lon` | 194 | 0 | 12.86750–13.11028 / 77.47808–77.74684 |

`WARDNO` ↔ `WARD_NAME` is perfectly 1:1 — no ward number maps to two names and
no name to two numbers. The register covers **103 of BBMP's 198 wards**.

`ZONE` (all 8 values, with counts):

| ZONE | Locations |
|---|---:|
| West | 38 |
| South | 34 |
| Mahadevapura | 30 |
| RR Nagar | 29 |
| East | 28 |
| Bommanahalli | 19 |
| Dasarahalli | 11 |
| Yelahanka | 11 |
| **Total** | **200** |

**Six coordinate pairs are shared by 11 rows** — e.g. three distinct Nandini
Layout locations ("Near ward office", "Back of Presidency school", "3rd
circular road") all sit at exactly `13.009511, 77.535528`. Those coordinates
are ward-level placeholders, not surveyed positions. Treat coordinate
precision as ~ward-centroid for that subset.

**`bbmp_low_lying_areas.kml` — 129 placemarks.** Fields: `OBJECTID` and
`<name>` only. 128 distinct names (one duplicate). **One row has no
coordinates at all**: `KARAMCHAND LAYOUT NEAR KARIYANNA PALYA` (OBJECTID 83).
No ward attribution of any kind.

**`flood_prone_locations.kml` — 70 placemarks.** Fields: `OBJECTID` and
`<name>` only. 67 distinct names; three names appear twice at genuinely
different coordinates (`Binny Mill Tank Area`, `Kamakshipalya Tank Slum Area`,
`NGV to HSR Layout`) — these are extended areas represented by two points, not
duplicate rows. No ward attribution. One name has a trailing newline inside
the `<name>` element (`Bhadrappa layout\n`), so names need stripping.

### 8.2 The three layers are near-disjoint

They are three *different* registers, not three versions of one. Spatial
overlap at a 150 m threshold:

| Layer A | Points in A with a point of B within 150 m | B |
|---|---:|---|
| `flood_prone` (70) | 3 (4%) | `flood_vulnerable` |
| `low_lying` (128) | 3 (2%) | `flood_vulnerable` |
| `flood_prone` (70) | 6 (9%) | `low_lying` |

By name the overlap is smaller still — 390 distinct names across 399 rows.

So the candidate location set is roughly **390–399 locations, not the ~210
assumed in `CLAUDE.md`**. `flood_vulnerable_map.kml` alone (200 points, ward
attributed, KGIS-sourced) is the closest match to that assumption and is the
only layer carrying ward attribution, so it is the natural primary register.
The other two are unattributed supplementary point sets.

### 8.3 Ward names do not join across the two datasets

Comparing the register's 103 ward names against the complaints' 198:

| Match attempt | Wards matched (of 103) |
|---|---:|
| Exact string equality | **55** |
| Lowercased, all non-alphanumerics stripped | 65 |
| Remaining unmatched | **38** |

The residue is transliteration variance — Kannada place names romanised
differently by two agencies — not different places:

| Hotspot register | Complaint CSV | Similarity |
|---|---|---:|
| `Bagalakunte` | `Bagalagunte` | 0.91 |
| `Bilekhalli` | `Bilekahalli` | 0.95 |
| `Binnypete` | `Binnipet` | 0.82 |
| `Cottonpete` | `Cottonpet` | 0.95 |
| `Dattatreya Temple` | `Dattathreya Temple` | 0.97 |
| `Dodda Bidarakallu` | `Dodda Bidarkallu` | 0.97 |
| `Hanumanth Nagar` | `Hanumantha Nagar` | 0.97 |
| `Hebbala` | `Hebbal` | 0.92 |
| `Rammurthynagar` | `Ramamurthy Nagar` | 0.97 |
| `Suddgunte Palya` | `Sudduguntepalya` | 0.97 |
| `Vijnana Nagar` | `Vignana Nagar` | 0.92 |
| `Yelahanka Satellite Town` | `Yelahanka old Satellite Town` | 0.94 |

…and 26 more in the same vein. All 38 find a candidate above 0.60 similarity,
**but fuzzy matching must not be applied blindly.** At least three pairings it
produces are wrong or unsafe:

- `Kadu Malleshwar` → `Malleshwaram` (0.77) — **two different wards.**
- `Kempapura` → `Kempapura Agrahara` (0.69) — **two different wards.**
- `Halsoor` → `Ulsoor` (0.77) — correct (Halasuru *is* Ulsoor), but knowable
  only from local knowledge, not from string distance.

**Recommendation: build a hand-checked ward crosswalk table and commit it**
(`data/reference/ward_crosswalk.csv`, keyed on `WARDNO` 1–198). The register
supplies an authoritative ward number for all 103 of its wards; the complaints
supply only names. A crosswalk is a few hours of work, is auditable, and is a
legitimate methods-section artifact. Fuzzy matching at load time would
silently misassign wards and corrupt every downstream memory value — exactly
the failure mode `CLAUDE.md` warns about for the complaint parser.

---

## 9. Cross-year inconsistencies

### 9.1 Column names — clean

No renames, no additions, no reordering. Identical header in all six files.

### 9.2 Encoding — clean

All nine files are valid UTF-8, no BOM, no mojibake, no mixed encodings. Byte
counts of non-ASCII characters are low and decode correctly.

One caveat: **fields contain embedded newlines inside quoted values**, so the
files cannot be split on line boundaries. Any parser must be a real CSV
reader, not a `readlines()` loop.

| Year | Field values containing a newline |
|---|---:|
| 2020 | 499 |
| 2021 | 340 |
| 2022 | 122 |
| 2023 | 147 |
| 2024 | 969 |
| 2025 | 939 |

### 9.3 Date format — clean

One format, all six years, zero unparseable values. But see §6 for the
AM/PM loss, which affects all years equally.

### 9.4 `Category` vocabulary — **changed substantially**

32 distinct values across the union; 21 in 2020 rising to 31 in 2025.

| Category | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | **Total** |
|---|---:|---:|---:|---:|---:|---:|---:|
| `Electrical` | 33,822 | 50,229 | 56,892 | 51,892 | 75,155 | 42,138 | **310,128** |
| `Solid Waste (Garbage) Related` | 24,022 | 24,184 | 22,828 | 28,639 | 57,329 | 38,151 | **195,153** |
| `Road Maintenance(Engg)` | 16,372 | 16,680 | 21,485 | 17,901 | 24,973 | 14,124 | **111,535** |
| `Forest` | 4,349 | 2,640 | 3,821 | 5,760 | 11,723 | 6,325 | **34,618** |
| `Health Dept` | 3,223 | 2,435 | 2,431 | 3,133 | 15,324 | 3,378 | **29,924** |
| `veterinary` | 3,876 | 2,785 | 3,019 | 3,396 | 4,771 | 7,677 | **25,524** |
| `Road Infrastructure` | 3 | 148 | 2,498 | 2,636 | 4,870 | 2,662 | **12,817** |
| `Others` | 1,113 | 772 | 811 | 472 | 2,809 | 2,066 | **8,043** |
| `Storm  Water Drain(SWD)` | 859 | 940 | 1,225 | 933 | 1,677 | 987 | **6,621** |
| `Revenue Department` | 1,337 | 470 | 557 | 449 | 1,062 | 1,283 | **5,158** |
| `E khata / Khata services` | — | — | — | — | 441 | 4,190 | **4,631** |
| `Town Planning` | 176 | 222 | 513 | 1,326 | 1,813 | 572 | **4,622** |
| `Parks and Play grounds` | 343 | 406 | 550 | 643 | 1,130 | 785 | **3,857** |
| `Advertisement` | 118 | 201 | 457 | 487 | 854 | 699 | **2,816** |
| `Sanitation` | 419 | 355 | 379 | 473 | 596 | 311 | **2,533** |
| `Lakes` | 259 | 224 | 471 | 440 | 587 | 318 | **2,299** |
| `CORONA COVID19` | 1,137 | 587 | 166 | 22 | 50 | 18 | **1,980** |
| `Water Crisis` | — | — | — | 2 | 700 | 261 | **963** |
| `Markets` | 30 | 33 | 7 | 70 | 209 | 196 | **545** |
| `Optical Fiber Cables (OFC)` | 47 | 102 | 106 | 139 | 81 | 40 | **515** |
| `Traffic Engineer Cell (TEC)` | — | — | 3 | 10 | 296 | 153 | **462** |
| `Indira Canteen` | — | — | — | 66 | 106 | 175 | **347** |
| `Information Technology` | — | — | — | 74 | 110 | 66 | **250** |
| `Estate` | 61 | 45 | 20 | 18 | 39 | 60 | **243** |
| `Plastic` | — | 7 | 42 | 60 | 95 | 29 | **233** |
| `Welfare Schemes` | 37 | 22 | 31 | 29 | 23 | 32 | **174** |
| `Call Center` | — | — | 1 | 41 | 55 | 72 | **169** |
| `Projects Central` | — | — | — | 3 | 84 | 60 | **147** |
| `Property Tax services` | — | — | — | — | 18 | 125 | **143** |
| `BBMP Election Branch` | — | — | 59 | 19 | 17 | 7 | **102** |
| `Education` | 17 | 17 | 21 | 6 | 19 | 14 | **94** |
| `Major Roads` | — | — | 1 | 1 | — | — | **2** |

Notes that bite:

- **`Storm  Water Drain(SWD)` contains a double space** between "Storm" and
  "Water". An exact-match filter written from the obvious spelling silently
  returns zero rows. This is the highest-value trap in the dataset.
- **`veterinary` is lowercase** while every other category is Title Case;
  `CORONA COVID19` is uppercase. Category matching must be case-insensitive.
- **`Road Infrastructure` appears with 3 rows in 2020 then jumps to 2,498 in
  2022** — it was introduced mid-2021 and likely absorbed rows that previously
  went to `Road Maintenance(Engg)`. Do not read that as a real-world change.
- `Major Roads` exists in 2022–2023 with **2 rows total** — a data-entry
  artifact, not a category.
- 11 categories are absent in 2020 and appear later. None of them are
  waterlogging-related, so the filter is unaffected — but any *year-over-year
  category composition* analysis is invalid without accounting for this.

### 9.5 `Grievance Status` vocabulary — **changed, with a silent rename**

| Grievance Status | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | **Total** |
|---|---:|---:|---:|---:|---:|---:|---:|
| `Closed` | 80,265 | 93,373 | 113,229 | 115,430 | 190,171 | 109,410 | **701,878** |
| `Registered` | 590 | 510 | 1,411 | 1,367 | 6,269 | 10,257 | **20,404** |
| `Rejected` | 6,763 | 6,544 | 3,496 | — | — | — | **16,803** |
| `Non Relevant` | 14 | 17 | 128 | 1,650 | 9,123 | 5,118 | **16,050** |
| `Resolved` | 3,964 | 2,989 | — | — | — | — | **6,953** |
| `ReOpen` | 14 | 20 | 34 | 57 | 918 | 1,656 | **2,699** |
| `In Progress` | — | 6 | 23 | 510 | 357 | 359 | **1,255** |
| `Long Term Solution` | 7 | 28 | 73 | 126 | 178 | 120 | **532** |
| `null` | 3 | 17 | — | — | — | 54 | **74** |

- **`Resolved` disappears after 2021** and **`Rejected` after 2022.** Their
  volume is absorbed by `Closed` and `Non Relevant` respectively — note
  `Non Relevant` rising from 128 (2022) to 1,650 (2023) as `Rejected` vanishes.
  A status-based filter (e.g. "count only resolved complaints") would produce
  a spurious 2022 discontinuity.
- Treat `Closed` + `Resolved` as one terminal state, and `Rejected` +
  `Non Relevant` as another.

### 9.6 `Sub Category` vocabulary — **grew 69%**

| Year | Distinct `Sub Category` | New vs prior year | Dropped vs prior year |
|---|---:|---:|---:|
| 2020 | 106 | — | — |
| 2021 | 107 | 2 | 1 |
| 2022 | 108 | 5 | 4 |
| 2023 | 120 | 14 | 2 |
| 2024 | 150 | 31 | 1 |
| 2025 | 179 | 31 | 2 |

Five values carry internal double spaces (`BBMP  Properties Lease issues`,
`Senior  Citizen`, `Unhygienic  premises in hospital`, and two more), and one
is wrapped in literal quote characters. Normalise whitespace before matching.

### 9.7 Volume — 2024 is anomalous

| Month | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|
| Jan | — | 8,325 | 8,381 | 6,999 | 11,069 | 18,702 |
| Feb | 6,704 | 8,151 | 7,544 | 7,145 | 12,133 | 17,957 |
| Mar | 9,717 | 9,315 | 8,653 | 8,105 | 12,092 | 21,366 |
| Apr | 4,962 | 7,367 | 6,985 | 5,902 | 10,953 | 21,656 |
| May | 7,181 | 6,284 | 11,896 | 10,182 | 17,660 | 26,805 |
| Jun | 9,011 | 8,225 | 11,520 | 10,953 | 20,345 | 20,488 |
| Jul | 7,820 | 9,181 | 11,260 | 12,749 | 22,189 | — |
| Aug | 7,837 | 8,355 | 11,669 | 12,584 | 20,935 | — |
| Sep | 9,567 | 10,209 | 11,660 | 11,556 | 18,223 | — |
| Oct | 11,340 | 10,472 | 10,667 | 11,711 | 24,094 | — |
| Nov | 9,113 | 9,522 | 8,672 | 11,052 | 18,711 | — |
| Dec | 8,368 | 8,098 | 9,487 | 10,202 | 18,612 | — |

Total volume nearly doubles in 2024 (207,016 vs 119,140 in 2023) and 2025 is
running higher still. This is **reporting-channel growth, not a doubling of
urban failure** — almost certainly app/portal adoption. It is exactly the
reporting-propensity confound named in `docs/01-evaluation-rules.md`, now
visible as a time trend rather than only a cross-sectional one.

**Any complaint count must be normalised against the ward's own contemporaneous
baseline, not against a fixed historical rate.** A location that looks
"emerging" in 2024 may simply be in a ward that adopted the app.

The May–October seasonal bulge is present in every year and is consistent with
the monsoon, which is the signal the project actually wants.

---

## 10. What this means for the loader

Concrete decisions for `app/ingestion/bbmp_complaints.py`, in priority order.

1. **Filter waterlogging on `Sub Category`, not `Category`. This is the single
   most consequential finding in the profile.** The `Storm  Water Drain(SWD)`
   category holds just 6,621 rows and contains only three sub-categories. The
   waterlogging signal mostly lives under **`Road Maintenance(Engg)`**:

   | Sub Category | Parent `Category` | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | **Total** |
   |---|---|---:|---:|---:|---:|---:|---:|---:|
   | `Road side drains` | Road Maintenance(Engg) | 3,476 | 3,330 | 4,520 | 4,382 | 5,367 | 3,269 | **24,344** |
   | `water stagnation` | Road Maintenance(Engg) | 1,040 | 1,085 | 1,743 | 999 | 2,127 | 1,280 | **8,274** |
   | `Maintenance of SWD` | Storm  Water Drain(SWD) | 558 | 528 | 780 | 549 | 989 | 547 | **3,951** |
   | `water leakage on road` | Road Maintenance(Engg) | 276 | 198 | 260 | 378 | 445 | 226 | **1,783** |
   | `Sewerage water left in SWD` | Storm  Water Drain(SWD) | 198 | 263 | 313 | 235 | 419 | 290 | **1,718** |
   | `Water related issue` | Water Crisis | — | — | — | 2 | 700 | 261 | **963** |
   | `Garbage thrown in storm water drain` | Storm  Water Drain(SWD) | 103 | 149 | 132 | 149 | 269 | 150 | **952** |
   | `Stagnation of water on road/ Water logging` | Projects Central | — | — | — | — | 8 | 2 | **10** |
   | `Drainage blockage` | Projects Central | — | — | — | — | 6 | 3 | **9** |
   | | | | | | | | | **42,004** |

   Distribution of those 42,004 rows by parent category:

   | Parent `Category` | Waterlogging rows | Share |
   |---|---:|---:|
   | `Road Maintenance(Engg)` | 34,401 | 81.9% |
   | `Storm  Water Drain(SWD)` | 6,621 | 15.8% |
   | `Water Crisis` | 963 | 2.3% |
   | `Projects Central` | 19 | 0.0% |

   **Filtering on `Category == 'Storm  Water Drain(SWD)'` would capture 6,621
   of 42,004 waterlogging complaints and silently discard 84% of the signal** —
   including `water stagnation`, the most direct waterlogging label in the
   dataset. This is precisely the "loader that silently drops rows" failure
   `CLAUDE.md` warns about, and it is invisible without this profile: the
   filter returns plausible non-zero output either way.

   The last two rows (`Stagnation of water on road/ Water logging`,
   `Drainage blockage`, 19 rows total, both under `Projects Central`, both
   2024–2025 only) are late vocabulary additions that never saw real use.
   Include them for completeness, but build no logic that depends on them.

2. **Solid waste is straightforward** — `Category == 'Solid Waste (Garbage)
   Related'` captures 195,153 rows across 13 sub-categories, with the bulk in
   `Garbage vehicle not arrived` (73,106), `Garbage dump` (66,680),
   `Sweeping not done` (20,774), and `Garbage dumping in vacant sites` (8,409).

   Note that **`Debris Removal / Construction Material` (14,810) is *not* under
   Solid Waste** — 14,809 of its rows sit under `Road Maintenance(Engg)`.
   Decide deliberately whether construction debris counts as solid waste for
   this project; the category assignment will not decide it for you.

3. **Expected post-filter volume: 42,004 waterlogging + 195,153 solid waste =
   237,157 rows, 30.9% of the 766,648 raw.** Comfortably inside the 1 GB free
   tier, vindicating rule 7 in `CLAUDE.md`.

   But note this is **well below the ~600k the build plan assumed** (`docs/00-build-plan.md`,
   "complaints ~600k after filtering"). The storage estimate there is safe; the
   *modelling* estimate may not be. 42,004 waterlogging complaints spread over
   198 wards and ~2,000 days is roughly 0.1 complaints per ward-day — a very
   sparse positive class. Revisit the base-rate assumption in
   `docs/01-evaluation-rules.md` once the panel is built.

4. **Normalise before matching.** Casefold, collapse internal whitespace, strip.
   Three separate traps (`Storm  Water Drain(SWD)`, lowercase `veterinary`,
   double-spaced sub-categories) all disappear under one normalisation step.
   Do **not** normalise the stored value — normalise only the comparison key,
   so the raw vocabulary stays auditable.

5. **`--inspect` mode is still worth building**, as `CLAUDE.md` requires, but
   its job is now narrower: assert that the header still matches the nine-column
   signature above and that the filter still returns a non-zero count. If BBMP
   republishes with a changed vocabulary, that assertion is what catches it.

6. **Load dates as `DATE`.** See §6.

7. **Do not attempt the location join in the complaint loader.** Complaints
   resolve to a ward; the hotspot register resolves to a point. Those meet only
   through the crosswalk of §8.3, which does not exist yet. Load complaints
   keyed on ward, load the register keyed on `WARDNO`, and build the crosswalk
   as its own reviewed artifact before `geo.py` runs.

## 11. Open questions

- **Which KML layer is the official register?** `flood_vulnerable_map.kml` is
  the only ward-attributed layer and the only one with a KGIS id, so it is the
  working assumption. The other two (199 further points) have no provenance
  metadata and no publication date. Worth an RTI or a mail to OpenCity, since
  "the city's own list" is load-bearing for the project's framing.
- **`CLAUDE.md` says ~210 flood-prone locations, 58 highly prone.** The files
  give 200 in the primary layer and 399 across all three, with no severity or
  "highly prone" field anywhere. The 58 figure has no support in this data —
  find its source or drop the claim.
- **No ward population or area** is present in any file, so complaints-per-capita
  (evaluation rule: control for ward baseline) needs a Census join not yet
  sourced.

---

## 12. Ward-day base rate, and the rainfall split

Added 7 Sep 2026, after loading Open-Meteo rainfall. This is the first
measured statement about how often the thing we are trying to predict
actually happens.

### 12.1 The panel

| | |
|---|---|
| Covered period | 2020-02-08 → 2025-06-19 (complaint coverage, §6) |
| Days | 1,959 |
| Wards | 198 (`NON Ward` excluded) |
| **All ward-days** | **387,882** |

A ward-day is counted in the denominator whether or not anything was
reported there, which is the point — the denominator is the full panel, not
the set of days that happen to appear in the complaint file.

### 12.2 Headline rates

Using the nine waterlogging sub-categories identified in §10.1 ("broad"), and
the IMD rainy-day threshold of 2.5 mm:

| | Ward-days with ≥1 waterlogging complaint | of | Rate |
|---|---:|---:|---:|
| **All ward-days** | **30,993** | 387,882 | **7.99%** |
| **On rainy ward-days** (≥2.5 mm) | **11,756** | 115,632 | **10.17%** |
| **On dry ward-days** (<2.5 mm) | **19,237** | 272,250 | **7.07%** |

**Lift from rain: 1.44×.** That is far weaker than expected, and §12.4
explains why.

Threshold sensitivity — the weak lift is not an artifact of where the line
is drawn:

| Rain threshold (city mean) | Wet days | Dry days | Rate wet | Rate dry | Lift |
|---|---:|---:|---:|---:|---:|
| any measurable (≥0.1 mm) | 1,163 | 796 | 9.06% | 6.43% | 1.41 |
| ≥1.0 mm | 833 | 1,126 | 9.71% | 6.72% | 1.45 |
| **IMD rainy day (≥2.5 mm)** | 584 | 1,375 | **10.17%** | **7.07%** | **1.44** |
| ≥10 mm | 176 | 1,783 | 12.52% | 7.54% | 1.66 |
| ≥25 mm | 14 | 1,945 | 12.88% | 7.96% | 1.62 |

### 12.3 The base rate is not 0.5%

`CLAUDE.md` rule 3 and `docs/01-evaluation-rules.md` both assume a base rate
of ~0.5%. At **ward-day granularity the measured rate is 7.99% — sixteen times
higher.**

These are not contradictory, they are different units. A ward is large (198
wards for ~13 M people, so ~65,000 residents each), so "something waterlogging-
related was reported somewhere in this ward today" is a much easier event than
"this specific hotspot flooded today". The 0.5% figure presumably refers to
**location-days** over the ~200–400 register locations, which cannot be
computed yet because the ward crosswalk does not exist (§8.3).

Two things follow:

- **The 0.5% figure is currently unsourced.** Nothing in the data supports it
  yet. Either derive it once locations are joinable, or stop quoting it.
- **The "never report accuracy" rule still holds and is unaffected.** At a
  7.99% base rate an always-negative classifier still scores 92% accuracy;
  at 1.56% (§12.4) it scores 98.4%. The argument for precision@k and PR-AUC
  does not depend on the exact figure.

### 12.4 Most of the signal is routine maintenance, not flooding

Splitting the 1.44× lift by sub-category shows it is an average over two
completely different behaviours:

| Sub Category | Ward-days | Rate wet | Rate dry | **Lift** |
|---|---:|---:|---:|---:|
| `water stagnation` | 6,029 | 2.95% | 0.96% | **3.07** |
| `Maintenance of SWD` | 3,321 | 1.19% | 0.72% | 1.66 |
| `Garbage thrown in storm water drain` | 867 | 0.28% | 0.20% | 1.44 |
| `Sewerage water left in SWD` | 1,518 | 0.48% | 0.35% | 1.35 |
| **`Road side drains`** | **20,500** | **6.41%** | **4.81%** | **1.33** |
| `Water related issue` | 888 | 0.24% | 0.23% | 1.05 |
| `water leakage on road` | 1,683 | 0.44% | 0.43% | 1.03 |
| *(all nine combined)* | 30,993 | 10.17% | 7.07% | 1.44 |

`Road side drains` is **66% of all waterlogging ward-days and barely responds
to rain** (1.33×). It is a request to clean or repair a drain — a maintenance
backlog item that can be filed on any dry Tuesday — not a report that
something flooded. Because it dominates the count, it drags the combined lift
down to 1.44 and makes the label look weather-insensitive.

`water stagnation` behaves the way a flood label should: **3.07× lift**, and
it is the sub-category whose plain meaning is "there is water sitting here".

**A strict event label** — `water stagnation` + `Stagnation of water on road/
Water logging` + `Drainage blockage` (8,293 complaints):

| | Ward-days | of | Rate |
|---|---:|---:|---:|
| **All ward-days** | **6,045** | 387,882 | **1.56%** |
| **On rainy ward-days** (≥2.5 mm) | **3,417** | 115,632 | **2.96%** |
| **On dry ward-days** (<2.5 mm) | **2,628** | 272,250 | **0.97%** |

**Lift 3.06×**, and it holds across every threshold (3.45× at ≥0.1 mm, 3.64×
at ≥10 mm). This is a label that responds to weather.

### 12.5 Recommendation

**Model two distinct targets, do not merge them.**

- **Failure events** — `water stagnation` and the two tiny stagnation/blockage
  sub-categories. Base rate 1.56%, rain lift 3.1×. This is the waterlogging
  label for `failure_memory` and the triage ranking.
- **Maintenance demand** — `Road side drains`, `Maintenance of SWD`, and the
  rest. Base rate 5.3% for `Road side drains` alone, rain lift 1.3×. This is
  a useful *feature* (a ward with a chronic drain backlog is plausibly more
  failure-prone) and a legitimate second output, but it is not a flood.

Training M1–M3 against the broad label would ask the model to predict a
maintenance backlog using rainfall, and it would deservedly fail. The `M0`
rainfall-threshold baseline would look strong against the strict label and
weak against the broad one — so **which label is chosen partly determines
whether Proof One succeeds**, which makes it a decision to record explicitly
rather than one to settle by whichever filter was written first.

### 12.6 Two caveats on these numbers

1. **Rainfall is city-wide, not per-ward. TESTED AND REJECTED AT 9 km — see
   §17.** This caveat predicted a per-ward join would raise every lift figure.

   The first attempt (§16) could not test it: 89% of wards shared one ERA5
   cell, so that run demonstrated ERA5's limits rather than testing the
   hypothesis. §17 then ran the real test on ECMWF-IFS, which resolves BBMP
   into **14 cells instead of 3** (modal cell 28%, 2.8× the across-ward
   spread, mixed wet/dry verdicts on 21% of days). Per-ward rainfall still
   moves the strict lag-0 lift only 3.06 → 3.00, **χ², p = 0.877**, and the
   precision@20 restriction still costs −6.0%.

   **Quote the city-mean figures without apology.** Tripling the resolution
   changes nothing measurable, so the limiting factor is not rainfall
   resolution. Substituting the max across cells for the mean changes the
   broad lift only from 1.44 to 1.46, so the conclusion is not sensitive to
   that choice either.

   Still open at *gauge* resolution (~1 km), which is a different order of
   magnitude — but §18 finds the gauge time series is not obtainable, and
   §17.4 shows weather alone ranks at chance regardless.
2. **A reporting lag exists but is small.** Shifting rainfall back one day
   raises the broad lift from 1.44 to 1.46 and the strict lift from 3.06 to
   3.13; by three days both are below the same-day figure. Same-day and
   previous-day rain are the informative windows.

Daily rainfall correlates with waterlogging ward-day counts at r = 0.32 daily
and r = 0.47 on monthly means — positive and real, but weak enough that
rainfall alone will not rank locations. That is the argument for the Failure
Memory Index, and it is now measured rather than asserted.

### 12.7 Reproducing this

```bash
python -m app.ingestion.cli weather --city Bengaluru --start 2019-01-01 --end 2025-06-30
python -m app.ingestion.cli weather-daily --city Bengaluru
python -m app.ingestion.cli status
```

512,568 hourly rows across 9 ERA5 cells, aggregated to 21,357 cell-days
(2019-01-01 → 2025-06-30). The 2019 lead-in exists so that `antecedent_7d_mm`
and the expanding-window percentiles have history before the complaint period
opens. Both commands are idempotent.

Loaded annual totals sanity-check against Bengaluru's ~970 mm normal, and
reproduce known years: 2023 at 726 mm (Karnataka's drought year) and 2021 at
1,382 mm (a record wet year).

---

## 13. Reporting lag

Added 7 Sep 2026. Strict event label (§12.4), rain threshold 2.5 mm city mean.

A complaint is filed when someone notices and reports, which need not be the
day it rained. If the lag were material, aligning rainfall to the complaint
date would understate every weather effect in the project.

| Rainfall series | Wet events | of ward-days | Dry events | of ward-days | Rate wet | Rate dry | **Lift** |
|---|---:|---:|---:|---:|---:|---:|---:|
| **same day (lag 0)** | 3,417 | 115,632 | 2,628 | 272,250 | 2.955% | 0.965% | **3.06** |
| lagged 1 day | 3,450 | 115,632 | 2,595 | 272,052 | 2.984% | 0.954% | **3.13** |
| lagged 2 days | 3,252 | 115,632 | 2,793 | 271,854 | 2.812% | 1.027% | **2.74** |
| lagged 3 days | 3,078 | 115,434 | 2,967 | 271,854 | 2.667% | 1.091% | **2.44** |
| max over prior 3 days | 4,488 | 177,210 | 1,557 | 210,672 | 2.533% | 0.739% | **3.43** |

### No — lag 1 does not materially beat lag 0

Lag 1 raises the lift from 3.06 to 3.13, a 2.3% relative gain. In absolute
terms that is **33 extra ward-day events out of 3,417**, on an identical
denominator of 115,632 ward-days. A chi-squared test on the two wet-day rates
gives **p = 0.695** — indistinguishable from noise.

Lag 2 (2.74) and lag 3 (2.44) are both clearly *worse* than same-day, and the
monotone decline from lag 1 onward is what a genuine same-day signal decaying
under mis-alignment looks like. If complaints were systematically filed a day
after the rain, lag 1 would stand out and lag 0 would be the weak one. It is
the other way round.

**Conclusion: align rainfall to the complaint date. Use lag 0.** Carry lag-1
rainfall as an extra feature if a model wants it, but do not shift the label,
and do not claim a reporting lag was found — the data does not show one.

### The 3-day window is better, but for a different reason

"Max rainfall over the prior three days" gives the highest lift in the table
(3.43). That is a real improvement, but reading it as "a wider window locates
events better" would be wrong. Compare it to lag 0:

- the wet-day event rate **falls**, 2.955% → 2.533%
- the dry-day event rate falls **further**, 0.965% → 0.739%

The window flags 895 days as wet instead of 584, sweeping marginal days into
the wet group and diluting it. All of the gain comes from the denominator: what
remains in the dry group is now genuinely dry *spells* rather than isolated dry
days sitting inside a wet week. So the 3-day window is a better description of
**antecedent dryness**, not a better detector of event days — which is exactly
the role `antecedent_7d_mm` already plays in `weather_daily`.

For ranking locations on a given night, same-day rainfall remains the right
alignment.

---

## 14. Spatial concentration, and the static baseline Proof One must beat

Added 7 Sep 2026. Strict event label, 2.5 mm threshold, ward level throughout —
**no ward crosswalk required**, so this is computable today.

### 14.1 The historically-worst list is stable

Splitting the period in half (H1 2020-02-08 → 2022-10-14, 2,835 events;
H2 2022-10-14 → 2025-06-19, 3,210 events) and ranking all 198 wards by event
count within each half:

| Comparison | Statistic |
|---|---|
| All 198 wards, H1 rank vs H2 rank | **Kendall tau = 0.590** (p = 8.8e-33) |
| All 198 wards, H1 vs H2 | Spearman rho = 0.756 |
| H1 top 20, their H1 rank vs their H2 rank | **Kendall tau = 0.400** (p = 0.015) |
| Top-20 set overlap between halves | **15 of 20** |

The list is persistent. Three quarters of the worst wards are still the worst
wards across a 2.7-year gap, and their internal ordering stays positively
correlated. **This is bad news for a naive system and good news for an honest
one**: it means "where does it flood" is close to a solved, static question,
exactly as `CLAUDE.md` argues. The value has to come from *when*.

### 14.2 The static ranking, trained and tested temporally

Train 2020-02-08 → 2023-12-31 (1,423 days). Freeze the top 20 wards by event
count. Test on the **138 rain days** in 2024-01-01 → 2025-06-19, carrying 1,289
strict events. The list is never updated during testing.

| # | Ward | Train events | Test rain-day events |
|---:|---|---:|---:|
| 1 | Bellandur | 156 | 21 |
| 2 | Horamavu | 130 | 36 |
| 3 | Thanisandra | 100 | 22 |
| 4 | Begur | 98 | 14 |
| 5 | Ramamurthy Nagar | 92 | 11 |
| 6 | Hoodi | 90 | 16 |
| 7 | Dodda Bidarkallu | 85 | 22 |
| 8 | Singasandra | 85 | 20 |
| 9 | Someshwara | 83 | 20 |
| 10 | Varthur | 76 | 25 |
| 11 | Rajarajeshwari Nagar | 72 | 13 |
| 12 | Bilekahalli | 64 | 8 |
| 13 | Jakkur | 64 | 26 |
| 14 | HBR Layout | 62 | 20 |
| 15 | Doddanekkundi | 60 | 30 |
| 16 | HSR Layout | 60 | 22 |
| 17 | Hagadooru | 55 | 14 |
| 18 | Byatarayanapura | 53 | 15 |
| 19 | Basavanapura | 48 | 12 |
| 20 | Herohalli | 44 | 7 |

The list is a sanity check in itself: Bellandur, Varthur, Hoodi, Doddanekkundi,
HSR Layout and Horamavu are the Outer Ring Road / Mahadevapura belt that
Bengaluru's press names every monsoon. The label is finding the places the city
already knows about — the premise of the project, now measured rather than
assumed.

**Share of events captured** on those 138 test rain days:

| List size | % of wards | Events captured | Share of all 1,289 | precision@k |
|---|---:|---:|---:|---:|
| top 5 | 2.5% | 104 | 8.1% | 15.07% |
| top 10 | 5.1% | 207 | 16.1% | 15.00% |
| **top 20** | **10.1%** | **374** | **29.0%** | **13.55%** |
| top 30 | 15.2% | 506 | 39.3% | 12.22% |
| top 40 | 20.2% | 583 | 45.2% | 10.56% |
| top 60 | 30.3% | 779 | 60.4% | 9.41% |

10% of the wards carry 29% of the events — real concentration, roughly 2.9x,
but well short of a "a few wards account for everything" story.

### 14.3 The number to beat

> ### **precision@20 = 13.6%**
>
> Ranking wards by prior event count alone, frozen at the end of 2023 and
> evaluated on the 138 rain days of 2024-2025.
>
> **This is the static baseline. M3 must beat it, and beating it is the
> substance of Proof One.**

Context for that figure, all on the same test set:

| Benchmark | precision@20 |
|---|---:|
| Random 20 wards | 4.72% |
| **Static "20 historically worst" (the baseline)** | **13.55%** |
| Same list re-ranked daily on all prior data | 13.70% |
| **Oracle ceiling** | **37.36%** |

Three things follow, and the third matters most.

**Precision@20 is capped at 37%, not 100%.** A rain day carries a mean of 9.3
and a median of 6 strict events across the whole city. Only 14 of the 138 test
rain days (10.1%) have 20 or more events, so on most nights fewer than 20 wards
*can* be right, and a perfect oracle would still score below 50%. Every
precision@20 figure this project reports must be printed beside this ceiling or
it will read as a failure when it is not. The static list achieves **36.3% of
the achievable maximum**.

**Re-ranking on more history adds nothing** (13.70% vs 13.55%). The static list
is already saturated: three further years of complaint counts do not improve
it. So the headroom between 13.6% and 37.4% is unreachable with memory alone —
it has to come from weather and from location-level features. That is the
argument for M3 restated as a measurement, and it is an encouraging result,
because the remaining 64% of achievable performance is exactly the space the
Failure Memory Index is designed to occupy.

**The baseline is not fragile.** Re-running with a 50/50 split (train to
2022-10-14, test on 246 rain days) gives precision@20 = 11.36% against a 3.56%
random baseline and a 29.70% ceiling — 38.3% of ceiling, the same story.

### 14.4 The baseline gets stronger as rain gets heavier

| Rain that day | Rain days | Mean events | Static precision@20 | Ceiling | % of ceiling |
|---|---:|---:|---:|---:|---:|
| 2.5-5 mm | 47 | 5.6 | 8.94% | 27.23% | 32.8% |
| 5-10 mm | 53 | 8.3 | 12.64% | 33.58% | 37.6% |
| 10-25 mm | 35 | 14.9 | 19.43% | 54.00% | 36.0% |
| >=25 mm | 3 | 20.3 | 33.33% | 68.33% | 48.8% |

Heavier rain produces more events, so both the achievable ceiling and the
static list's absolute score rise together. **Report precision@20 stratified by
rainfall, or at minimum on a fixed set of held-out rain events.** A model
evaluated on a wetter test period beats one evaluated on a drier period without
being any better, and the spread here (8.9% to 33.3%) is larger than any
plausible modelling gain.

### 14.5 What this means for Proof One

1. **The target is precision@20 > 13.6% on rain days, against a 37.4% ceiling.**
   Quote all three numbers together — achieved, baseline, ceiling — every time.
2. **Kendall tau between consecutive rankings must be judged against tau = 0.59**,
   the observed static persistence between period halves. A model whose nightly
   rankings correlate at 0.59 or above has reproduced the static list and has
   proved nothing, however good its precision looks.
3. **Block the test set by rainfall band**, per §14.4.
4. These figures are ward-level. Once the crosswalk exists, re-run the same
   analysis at location level, where 20 of ~390 locations is a far more
   selective ask than 20 of 198 wards and the baseline will be lower.
   **The ward-level 13.6% is a floor for the location-level baseline, not a
   substitute for it.**

---

## 15. The ward crosswalk

> **Partly superseded by §16.** The artifact described here was rebuilt on the
> 198-ward BBMP boundary file, which covers every ward rather than the
> register's 103. The **method** below still stands and the hand decisions were
> all independently confirmed — but the CSV's columns and the coverage counts
> are now those in §16.1. Read this section for how the decisions were made,
> §16 for what the file contains today.

Added 7 Sep 2026. Artifact: `data/reference/ward_crosswalk.csv`.
Loader-side rule: `app/ingestion/ward_crosswalk.py`.
Tests: `tests/test_ward_crosswalk.py` (21).

§8.3 established that the complaints and the hotspot register cannot be joined
on ward name. This section records the hand-checked crosswalk that fixes it,
and — more importantly — what it does *not* fix.

### 15.1 Coverage

One row per complaint ward name, 198 rows, each name appearing exactly once.

| `match_method` | Wards | Complaint rows | Share of rows |
|---|---:|---:|---:|
| `exact` | 55 | 279,210 | 36.42% |
| `normalised` | 20 | 73,614 | 9.60% |
| `manual` | 27 | 104,810 | 13.67% |
| `not_in_register` | 96 | 309,012 | 40.31% |
| `unresolved` | **0** | **0** | **0.00%** |
| **mapped to a ward number** | **102** | **457,634** | **59.69%** |

**Nothing is unresolved.** Every one of the 198 complaint ward names was
either mapped to a register ward number or positively identified as a ward the
register does not cover.

Share is reported on complaint **rows**, not ward names, because one busy ward
matters more than ten quiet ones. The row-weighted picture is close to the
ward-weighted one here (59.7% of rows vs 51.5% of wards), so no single
high-volume ward is doing outsized damage.

### 15.2 Two corrections to the task spec

**The crosswalk has 198 rows, not 103.** `NEXT.md` says "every one of the 103
complaint ward names". 103 is the count of ward names in the *register*; the
complaints carry **198**. The artifact is keyed on `complaint_ward_name`, so it
has one row per complaint ward. The 55-of-103 figure quoted in the task is a
register-side statistic and is unchanged.

**`match_method` needed a fifth value, `not_in_register`.** The spec's four
values have no way to say "this is a real ward that the register simply does
not list". The register covers flood-vulnerable locations in 103 of 198 wards,
so 96 complaint wards have no register entry at all. That is a fact about the
register's scope, not a failure to resolve a name.

This matters because of the exclusion rule. Marking those 96 `unresolved` and
excluding them would have dropped **309,012 rows, 40.31% of the dataset**,
under the label of routine data cleaning — precisely the "shrinking panel
nobody notices" failure the task warns about. So:

- `unresolved` → excluded from the panel, logged loudly.
- `not_in_register` → **kept**. The ward exists, its number is merely not
  recoverable from this source. It has complaints, it has a name, and it
  belongs in every ward-level analysis.

Only wards that need a *location* (nearest weather cell, hotspot join) require
the ward number. Ward-level work — everything in §12, §13 and §14 — needs only
the name, and is unaffected.

### 15.3 Method

1. **Exact** — casefold, collapse whitespace. 55 wards.
2. **Normalised** — a fixed set of documented Kannada-to-Latin folds applied to
   both sides: `oo`/`u`, `ee`/`i`, `th`/`t`, `w`/`v`, aspirated consonants
   (`bh`→`b` and friends), trailing vowel drift, doubled letters, and a
   dropped trailing `Ward`. A match counted only when the normal form was
   unique on the register side. 20 wards, each verified by eye afterwards.
3. **Manual** — 27 wards resolved one at a time against the register's ward
   **number**, BBMP **zone**, and point **centroid**. Every row carries a note
   giving the evidence.
4. **Unresolved** — none needed.

**No ward number was assigned by fuzzy string matching.** Fuzzy scores were used
only to shortlist candidates for human review, exactly as the task requires.
Three of the pairings string distance suggests are wrong or unjustifiable, and
each was decided on other evidence:

| Pair | String verdict | Actual decision |
|---|---|---|
| register `Kadu Malleshwar` → `Malleshwaram` | 0.77, plausible | **Rejected.** `Malleshwaram` matches register `Malleshwaram` (ward 45) *exactly*. BBMP lists Kadu Malleshwara and Malleswaram as separate wards. Left unpaired. |
| register `Kempapura` → `Kempapura Agrahara` | 0.69, flagged as wrong in §8.3 | **Accepted on coordinates.** Ward 122 sits between Cottonpete (120) and Vijayanagar (123) at 12.972, 77.554 — exactly Kempapura Agrahara. Not the Hebbal Kempapura, which is near 13.05. |
| register `Halsoor` → `Ulsoor` | 0.77, weak | **Accepted on local knowledge.** Halasuru *is* Ulsoor — the Kannada name against the anglicised one. Centroid 12.978, 77.627 confirms. String distance alone would never justify this. |

The `Kempapura Agrahara` row is marked in the CSV as the **lowest-confidence
decision in the file**. If one row gets re-checked by a second person, it is
that one. It carries 903 complaint rows, 0.12% of the dataset, so the blast
radius if wrong is small.

### 15.4 One register ward could not be paired

**Register ward 65, `Kadu Malleshwar`** (West zone, 13.003, 77.564) has no
complaint-side partner. The obvious candidate is already taken: complaint
`Malleshwaram` matches register `Malleshwaram` at ward 45 exactly. The nearby
unmatched complaint wards — `Subramanya Nagar`, `Gayathri Nagar`,
`Marappana Palya` — are all plausibly separate wards in their own right, and
guessing between them would be exactly the error this artifact exists to avoid.

So 102 of the register's 103 wards are claimed. Ward 65's single
flood-vulnerable location cannot currently be attributed to a complaint ward.
**Resolve this against BBMP's published 198-ward list**, which neither source
here contains, rather than against these two files.

### 15.5 A defect in the register

`flood_vulnerable_map.kml` carries **ward 73 `Kottegepalya` twice with two
different `ZONE` values** — once as RR Nagar (12.966, 77.517) and once as
Dasarahalli (12.998, 77.517). The name-to-number mapping is unaffected, but
the register's `ZONE` field cannot be treated as authoritative. Use `WARDNO`.

### 15.6 The loader-side rule

`app/ingestion/ward_crosswalk.py` loads the CSV and validates it on every
construction: no duplicate complaint name, no register ward number claimed
twice, every `manual` and `unresolved` row carrying a note, and no row both
lacking a number and claiming a match method that implies one.

`apply_to_ward_series()` returns a keep-mask plus a report, and **logs the
excluded row count and share unconditionally on every run** — at `WARNING`
when anything is excluded. A ward name absent from the CSV raises rather than
being guessed at, with an error that names the file to edit.

Current state: **0 rows excluded.** When that changes, it will say so.

---

## 16. Per-ward rainfall: the recompute, and why it does not help

Added 7 Sep 2026. §12.6 predicted that replacing city-wide mean rainfall with
per-ward rainfall would raise every lift figure, because Bengaluru's storms are
localised and a city mean labels 197 dry wards "rainy" whenever one corner
floods.

**That prediction was wrong.** Every figure moved slightly the wrong way. The
reason is a resolution limit that is worth stating plainly, because it also
constrains what M1 and M2 can ever learn from ERA5.

### 16.1 What changed upstream

`data/reference/ward_crosswalk.csv` was rebuilt on
**`bbmp_ward_map_2015.kml`, the 198-ward BBMP delimitation** in force for the
whole complaint period — not on the flood register. All 198 complaint ward
names now carry a BBMP ward number, a polygon centroid, a zone and an area.

| | Register-based (§15) | Boundary-based (§16) |
|---|---:|---:|
| Wards with a ward number | 102 | **198** |
| Complaint rows covered | 59.69% | **100%** |
| `exact` | 55 | 106 |
| `normalised` | 20 | 44 |
| `manual` | 27 | 48 |
| `unresolved` | 0 | **0** |

**All 102 register-derived ward numbers agree with the boundary file**, which
independently validates the §15 hand decisions, including the two contested
ones (`Ulsoor`→90, `Kempapura Agrahara`→122).

Polygon centroids, not register points, are the right geometry: a register
point is by definition a *flood-prone* spot, so using one as a ward's position
drags every ward toward low ground — a systematic bias in every distance
computed from it, not a missing-data problem.

`locations` now holds 198 ward rows (`geom_level='ward'`) plus 398 register
points (`geom_level='point'`, `is_known_hotspot=true`, `hotspot_source` naming
the layer). The three register layers are loaded **unmerged**; one low-lying
row is dropped because its KML coordinates are the literal string `nan,nan`.

### 16.2 The two wards the register could not resolve

§15.4 left BBMP ward 65 unpaired. The boundary file closes it, and turns up a
second case the register could not have shown:

- **`Someshwara` → ward 3.** No 198-ward is named Someshwara, and the complaint
  feed has no `Atturu`. In the **243-ward** delimitation
  (`bbmp_ward_map_2022.kml`) ward 3 is `Someshwara Ward` (centroid 13.1037,
  77.5744) and ward 4 is `Atturu Layout` (13.0957, 77.5550) — both carved out
  of the single 198-ward 3 `Atturu` (13.1028, 77.5600). The complaint feed is
  using the newer locality name for part of the old ward. 11,376 complaints.
- **`Subedarapalya` → ward 65** (`Kadu Malleshwar Ward`, West). Reached by
  elimination once Someshwara resolved: exactly one name and one ward left.
  Corroborated — Subedarpalya is a Malleshwaram-belt locality and ward 65's
  BBMP Division and Sub Division are both *Malleshwaram* — but not proved, so
  it is flagged in the CSV as the file's lowest-confidence row.

`NEXT.md` stated that ward 65 "is the complaint-side `Kadu Malleshwar`". That
is not quite right: `Kadu Malleshwar` is the *register* and *boundary* spelling.
No complaint ward carries that name. The gap was on the complaint side, and it
is `Subedarapalya` that fills it. The geography in the task note — ward 65
between Rajamahal (64) and Subrahmanyanagar (66) — is confirmed exactly.

### 16.3 The resolution limit

Each ward was assigned the nearest of the 9 ERA5 cells by haversine:

| Cell | Wards |
|---|---:|
| 5 (city centre) | **176** |
| 6 | 8 |
| 8 | 7 |
| 4 | 4 |
| 2 | 3 |

**176 of 198 wards — 89% — share one cell.** Only 5 of the 9 cells are used at
all. The grid is 3×3 at 0.2°, about 22 km spacing, and BBMP spans roughly
0.26° × 0.28°, about 29 × 30 km. **The city is barely larger than one grid
step**, so almost every ward centroid is nearest the middle.

On 36.1% of days every ward receives an identical rainfall value. The five used
cells do differ — a mean daily max-minus-min spread of 2.94 mm — so there is
real spatial signal, but only 22 wards are positioned to receive it, and being
at the city's edge is not the same as being where the storm was.

### 16.4 §13 recomputed — reporting lag

| Rainfall series | City-mean lift | **Per-ward lift** | Change |
|---|---:|---:|---:|
| **lag 0 (same day)** | 3.06 | **2.89** | −5.6% |
| lag 1 | 3.13 | 3.08 | −1.6% |
| lag 2 | 2.74 | 2.66 | −2.7% |
| lag 3 | 2.44 | 2.34 | −4.1% |
| max over prior 3 days | 3.43 | 3.48 | +1.7% |

Per-ward, lag 0: 3,262 events on 111,924 wet ward-days (2.9145%) against 2,783
on 275,958 dry (1.0085%).

The wet-day event rate is statistically indistinguishable from the city-mean
version (**χ², p = 0.575**). Every conclusion in §13 survives unchanged: lag 0
is the right alignment, lag 1 is noise, lags 2–3 are worse, and the 3-day
window's edge is still denominator-driven.

### 16.5 §14 recomputed — the static baseline

The static ranking uses prior event counts only, so per-ward rainfall cannot
change the ranking. What it can change is *which wards are candidates on a
given night* — operationally the more useful question, since crews are only
sent where it is raining.

| Variant | Days | precision@20 | Ceiling | % of ceiling |
|---|---:|---:|---:|---:|
| (A) city-mean rain days, all 198 wards ranked | 138 | **13.55%** | 37.36% | 36.3% |
| (A′) the 123 of those days with ≥20 wet wards | 123 | 13.90% | 37.32% | 37.2% |
| (B) same 123 days, ranking **only wet wards** | 123 | **13.01%** | 35.45% | 36.7% |

Like-for-like, restricting the candidate pool to wet wards **lowers**
precision@20 by 6.4%.

The reason is in the numbers: on a typical rain day **173 of 198 wards are
already "wet"** at the 2.5 mm threshold, because 89% of them read the same
central cell. So the restriction removes only ~25 wards, and some of those
removed did have events — the ward was flooding while the cell it inherited
read dry. It costs more in lost true positives than it gains in discarded
candidates.

**The headline baseline is unchanged: precision@20 = 13.6%, ceiling 37.4%.**

### 16.6 What this means

> **Superseded in part by §17.** Point 1 below was right about ERA5 but wrong
> to generalise — a finer product exists, was tested, and resolves BBMP into 14
> cells. The conclusion survives anyway: it still does not help. Points 2 and 3
> are corrected here; read §17 for the tested versions.

1. **ERA5 cannot resolve intra-city rainfall for Bengaluru.** At ~25–31 km
   native resolution against a ~30 km city, per-ward weather from this source
   is one number with edge noise. Adding more cells to *this* grid will not fix
   it — the reanalysis has no finer structure to give. **It does not follow
   that no product can**: ECMWF-IFS at ~9 km gives 14 cells over the same city
   (§17.1).
2. **The §12.6 caveat is now tested, not merely untestable.** This run could
   not test it — with 89% of wards on one cell it demonstrated ERA5's limits.
   §17 ran the real test at 9 km and the hypothesis was rejected there
   (χ², p = 0.877). Quote city-mean numbers without apology, on that basis.
3. **This bounds M1, and the weather component of M2.** A weather-only ranker
   sees ~4.8 distinct rainfall values across 198 wards under ERA5 and 12.9
   under IFS, so its within-night ordering is largely arbitrary — about 14
   wards share every value. **M1 is not a weak baseline for triage, it is
   structurally close to degenerate.** Measured in §17.4: weather-only scores
   **5.63%** against a **4.80%** random baseline, while memory alone reaches
   **14.08%**. M2 is not affected the same way — terrain genuinely varies per
   ward — so this bounds M1 strictly and M2's weather features only.
4. **If genuine per-ward rainfall is wanted, it needs a different source.**
   KSNDMC operates telemetric rain gauges at ward granularity across Bengaluru
   — 131 inside BBMP, median 0.95 km from each ward centroid. **But the hourly
   series is not obtainable: §18 found only 5 reporting stations from August
   2023.** The pipeline works without it, and §17.4 is the evidence for saying
   so in the limitations.

### 16.7 Reproducing this

```bash
python -m app.ingestion.cli wards --city Bengaluru
python -m app.ingestion.cli status
```

Idempotent: `locations` holds 596 rows (198 wards + 398 points) before and
after a re-run.

---

## 17. Finer rainfall: tested, and it does not help

Added 7 Sep 2026. §16 concluded that ERA5 cannot resolve intra-city rainfall
and left open whether a finer product would. **It was tested. It does not.**

### 17.1 What Open-Meteo actually serves

The archive endpoint takes a `models=` parameter. Asking it to echo the snapped
grid-cell coordinate for each of the 198 ward centroids measures effective
resolution directly, without fetching any time series:

| Model | Distinct cells over BBMP | Modal cell holds | Native grid step |
|---|---:|---:|---|
| `era5` | **3** | 79% | 0.25° (27.8 km) |
| `era5_land` | 9 | 35% | 0.10° (11.1 km) |
| `ecmwf_ifs` | **14** | **28%** | 0.070° lat (7.8 km) |

BBMP spans 29.2 km N–S by 30.4 km E–W, so ERA5 genuinely gives the city three
cells. (Our production grid of nine 0.2° points was over-sampling a three-cell
reality — the nine points snapped onto three cells.)

**`era5_land` is unusable despite its grid**: Open-Meteo returns `null` for
every `precipitation` hour on that model. Verified over multiple date ranges.
It is fine for temperature; it cannot serve this project.

`ecmwf_ifs` (~9 km, 2017-present, so it covers the whole complaint period) is
the only finer option that works.

### 17.2 The wet-month test

One wet month, 2022-09, fetched at every distinct cell of each model and mapped
onto the 198 wards:

| | era5 | ecmwf_ifs |
|---|---:|---:|
| Distinct cells | 3 | **14** |
| Modal cell share | 79% | **28%** |
| Mean daily across-ward spread | 1.44 mm | **4.03 mm** |
| Median daily spread | 0.40 mm | 1.50 mm |
| Max daily spread | 10.8 mm | 20.9 mm |
| Mean across-ward SD | 0.31 | 0.98 |
| Days where all wards read alike | 10% | 7% |
| Days with a mixed wet/dry verdict | 1 of 30 | **7 of 30** |

The decision rule in the task was: stop if the modal cell still holds 80%+;
backfill if it drops to ~40% or below with a materially larger spread. It
dropped to **28% with 2.8× the spread**, so the backfill was run.

### 17.3 The backfill, and the result

797,328 hourly rows over the 14 native IFS cells, 2019-01-01 → 2025-06-30,
aggregated to 54,579 cell-days. All 198 wards reassigned to their nearest IFS
cell (56 / 28 / 26 / 26 / 20 / 9 / 8 / 6 / 5 / 4 / 3 / 3 / 2 / 2).

**§13 — lift, strict label, 2.5 mm threshold:**

| Rainfall series | ERA5 city-mean | IFS city-mean | **IFS per-ward** | vs ERA5 |
|---|---:|---:|---:|---:|
| **lag 0 (same day)** | 3.06 | 3.09 | **3.00** | −2.1% |
| lag 1 | 3.13 | 3.07 | 3.09 | −1.1% |
| lag 2 | 2.74 | 2.69 | 2.59 | −5.3% |
| lag 3 | 2.44 | 2.32 | 2.38 | −2.4% |
| max over prior 3 days | 3.43 | 3.45 | 3.40 | −0.8% |

lag 0 per-ward: 3,308 events on 111,496 wet ward-days (2.9669%) against dry
0.9903%. Versus ERA5 city-mean's 2.9551% / 0.9653%. **χ², p = 0.877.**

**§14 — static precision@20:**

| Variant | Days | precision@20 | Ceiling | % of ceiling |
|---|---:|---:|---:|---:|
| (A) ERA5 city-mean rain days, all wards | 138 | 13.55% | 37.36% | 36.3% |
| (B) IFS city-mean rain days, all wards | 136 | **14.08%** | 37.72% | 37.3% |
| (C) IFS rain days, ranking only wet wards | 136 | 13.24% | 34.34% | 38.5% |

Like-for-like, the per-ward restriction still costs **−6.0%**, essentially
identical to ERA5's −6.4%.

Why it does not help, even at 9 km: on an IFS city rain day **180 of 198 wards
are individually wet**, up from 173 under ERA5. A finer grid did not narrow the
candidate pool, it widened it — IFS is simply wetter (September 2022 median
ward total 101.5 mm against ERA5's 90.6 mm), so more wards clear 2.5 mm. The
grid does differentiate the city far better — a mixed wet/dry verdict on 411 of
1,959 days (21%) against ERA5's near-zero — but that differentiation does not
line up with where complaints appear.

**This is now a tested hypothesis, not an untestable one.** Tripling the
resolution, from 3 cells to 14, moves nothing measurable. The limiting factor
is not rainfall resolution.

### 17.4 Weather alone ranks at chance

The natural follow-up: if per-ward rainfall carries so little ranking
information, what does a weather-only ranker actually score? Ranking all 198
wards by their own cell's `rain_24h_mm` each night, ties broken randomly,
evaluated on the same 136 held-out rain days:

| Ranker | precision@20 | % of ceiling |
|---|---:|---:|
| Weather only — ERA5, 3 cells | 6.46% | 17.1% |
| Weather only — IFS, 14 cells | **5.63%** | 14.9% |
| **Random ward order** | **4.80%** | 12.7% |
| **Memory only — static top-20** | **14.08%** | 37.3% |
| Oracle ceiling | 37.72% | 100% |

**A weather-only ranking scores at chance.** 5.63% against a 4.80% random
baseline, and the *finer* model scores slightly lower than the coarse one —
because IFS spreads wards across 14 cells and breaks whatever accidental
blocking ERA5's three coarse cells provided. Neither is meaningfully above
random.

A ranker sees a mean of 4.8 distinct rainfall values across 198 wards under
ERA5, and 12.9 under IFS. Either way it is being asked to order 198 items using
about a dozen distinct keys, so within-cell order is arbitrary — 14 wards on
average share every value.

**This is the project's central claim, measured directly:**

> Memory alone reaches 14.1%. Weather alone reaches 4.8–5.6%, which is chance.
> The oracle ceiling is 37.7%. The entire climb from 14% to 37% has to come
> from the two interacting — which is exactly what M3 is.

### 17.5 What this settles, and what it does not

**Settled.** Reanalysis rainfall does not resolve which *ward* floods on a
given night, at 27 km or at 9 km. Report city-mean figures without apology.
§12.6's hypothesis has now been tested and rejected at 9 km.

**Not settled.** The hypothesis remains untested at *gauge* resolution (~1 km),
which is a different order of magnitude — a ward averages 3.7 km², while even a
9 km IFS cell is ~80 km², still 20 wards wide. §18 reports on what gauge data
is actually obtainable.

**Operationally, nothing changes.** The pipeline runs on IFS now because it is
strictly better data at no cost, and the headline numbers are unchanged within
noise. `weather_cells` 1–9 are ERA5 and 10–23 are ECMWF-IFS; `data_sources`
distinguishes them per observation via `weather_observations.source_id`.

---

## 18. KSNDMC telemetric gauges — locations yes, time series no

Timeboxed investigation, 7 Sep 2026. **Verdict: the gauge network is real and
dense, but the retrievable hourly data is not. Dead end for this project's
window unless KSNDMC is approached directly.**

### 18.1 The gauge network is excellent

From OpenCity, public domain, no credentials:

| Layer | Placemarks | Inside BBMP |
|---|---:|---:|
| `Karnataka - Telemetric Rain Gauges` | 5,929 | **131** |
| `Bengaluru Urban - Telemetric Rain Gauge Locations` | 185 | 129 |
| `Karnataka - Telemetric Weather Stations` | 740 | 11 |

Rain-gauge density inside BBMP, per ward centroid:

| | km |
|---|---:|
| Nearest gauge, minimum | 0.01 |
| **Nearest gauge, median** | **0.95** |
| Nearest gauge, p90 | 1.51 |
| Nearest gauge, maximum | 2.46 |

**195 of 198 wards are within 2 km of a gauge; all 198 within 3 km.** Density is
one gauge per ~9 km². Against 14 IFS cells for the whole city, this would be a
different class of measurement — genuine point observation at roughly ward
scale. A companion CSV lists 198 telemetric rain gauges with commissioning
dates from 2013, so the network predates the complaint window.

### 18.2 The time series is not available

National Water Data Portal, `rainfall-telemetry-hourly-karnataka-department`.
The CKAN API is open and needs no credentials. Three CSVs are listed:

| Resource | Size | Reality |
|---|---:|---|
| Rainfall Karnataka 1991–2020 | **342 bytes** | **Effectively empty — one row, dated 2008** |
| Rainfall Karnataka 2021–2025 | 83.5 MB | Real data, but see below |
| Rainfall Karnataka 2026–2030 | — | Future |

The 83.5 MB file holds 683,619 rows for **all of Karnataka** — 686 stations,
earliest timestamp **2021-08-08**, not 1991.

Narrowing to Bengaluru:

- Bangalore Urban + Rural districts: **21 stations**, data from **2023-07-15**.
- Inside the BBMP bounding box: **5 stations**, 3,092 rows, from **2023-08-06**.
- Nearest *reporting* station per ward: median **7.13 km**, only 10 of 198 wards
  within 2 km — worse in practice than the 9 km IFS grid.
- Hourly completeness ≈ 1.1% of hours. These look like event or threshold
  triggered records, not a continuous series.

So of 131 published gauge locations inside BBMP, **five report to the national
portal, and only from August 2023** — a ~23-month overlap with a complaint
window that ends June 2025, and nothing for 2020–2022.

### 18.3 Recommendation

**Stop spending on the NWDP route.** The gap is not our filtering: the data is
not on that portal.

The locations file proves the observations exist — KSNDMC holds them on its own
infrastructure. That is an RTI or a formal data request to KSNDMC / Karnataka
Revenue Department (Disaster Management), not a download. Worth one letter
given the payoff, but it is a months-scale ask with an uncertain answer and
**must not block the pipeline**.

Note the honest framing for the paper: §17.4 shows weather alone ranks at
chance, and that finding does not depend on rainfall resolution — a gauge
network would sharpen the weather features, not overturn the conclusion that
memory is what carries the ranking.

The four location files are in `data/raw/` (gitignored) and the analysis is
reproducible from the URLs in this section.

---

## 19. Is the headroom real? No — 93% of it is not ward-level

Added 8 Sep 2026. §17.4 left 23.6 points between the static baseline (14.08%)
and the oracle ceiling (37.72%). This section asks whether anything observable
reaches into that gap, before any model is built.

**Answer: no. A ward-level ranking fitted with perfect foresight — cheating,
using the test period's own outcomes — reaches 15.66%. That is 1.6 of the 23.6
points. The other 93.3% is within-ward temporal variation: knowing *which
night* a given ward fails, which nothing available predicts.**

### 19.1 The surprise set

A *surprise* is a ward with a strict event on a test rain day that is not in the
frozen top-20. On the 136 held-out IFS rain days (2024-01-01 → 2025-06-19):

| | |
|---|---:|
| Ward-days (198 wards × 136 nights) | 26,928 |
| Strict events | 1,289 |
| Events inside the frozen top-20 | 383 (29.7%) |
| **Surprises** | **906 (70.3%)** |
| Surprise base rate among non-top-20 ward-days | 3.743% (906 / 24,208) |

### 19.2 The static list is not simply cut too short

Where surprises sit in the prior-count ranking:

| Prior rank | Surprises | Share | Cumulative |
|---|---:|---:|---:|
| 21–40 | 215 | 23.7% | 23.7% |
| 41–60 | 194 | 21.4% | 45.1% |
| 61–100 | 195 | 21.5% | 66.7% |
| 101–198 | 302 | 33.3% | 100% |

Median surprise rank is **69**. Only **0.8%** come from genuinely cold wards
(zero prior events), so this is not unknown places flooding — it is
*mid-ranked* places flooding unpredictably.

Lengthening the list trades precision for recall and does not help:

| List | Events captured | precision@k |
|---|---:|---:|
| top-20 | 29.7% | **14.08%** |
| top-30 | 40.0% | 12.62% |
| top-40 | 46.1% | 10.92% |
| top-60 | 61.2% | 9.67% |
| top-80 | 70.7% | 8.37% |

### 19.3 Almost nothing is associated with surprise membership

Over the 24,208 non-top-20 ward-days:

| Feature | Mutual info | Point-biserial r | p |
|---|---:|---:|---:|
| *n wards flooded tonight* (post-hoc) | 0.0259 | **0.294** | ~0 |
| city rainfall | 0.0231 | 0.119 | 1.6e-76 |
| own-cell rain_24h | 0.0165 | 0.116 | 1.2e-73 |
| prior event count | 0.0049 | 0.113 | 5.3e-70 |
| prior rank | 0.0102 | −0.105 | 4.0e-60 |
| rain percentile | 0.0230 | 0.096 | 1.5e-50 |
| rain_3h_max | 0.0115 | 0.091 | 8.3e-46 |
| antecedent 7d | 0.0172 | 0.089 | 1.6e-43 |
| ward area | 0.0075 | 0.075 | 2.3e-31 |
| on the flood register | 0.0057 | 0.038 | 5.0e-09 |
| bowl (centroid below boundary) | 0.0093 | −0.027 | 2.3e-05 |
| elevation range | 0.0050 | 0.013 | 0.051 |
| season position | 0.0199 | −0.012 | 0.071 |
| elevation | 0.0072 | −0.007 | 0.255 |

Everything is significant, because n = 24,208; nothing is *large*. The single
strongest correlate is **post-hoc and night-level**: how many other wards
flooded tonight. That is the shape of the whole result — surprise membership is
mostly about which *night* it is, not which *ward*.

Terrain is the disappointment. `bowl` — centroid elevation minus mean boundary
elevation, sampled from the ward polygon — is the most physically motivated
feature here and correlates at −0.027. It does rank the right places
qualitatively (the most bowl-like wards are Shettyhalli, Horamavu, Ullalu,
Bagalagunte and Bellandur, several of them top-20 flood wards), but it adds
nothing once memory is in the model.

### 19.4 Why a good AUC hides the problem

A logistic model over all features reaches **held-out ROC-AUC 0.749** and
PR-AUC 0.116 against a 0.037 base rate — a 3.1× lift. That looks like success.
It is not, and the reason is a trap worth naming.

Variance decomposition of each feature across the test panel:

| Feature | Share of variance that is *between* nights |
|---|---:|
| season, city rainfall | 100% |
| antecedent 7d | 96.8% |
| own-cell rain_24h | 84.6% |
| rain percentile | 76.6% |
| rain_3h_max | 73.6% |
| own-cell rain minus city mean | 9.3% |
| area, elevation, bowl, prior count, register | **0%** |

Pooled AUC rewards separating bad nights from quiet ones. **precision@k only
ever compares wards *within* one night.** So the two can diverge completely:

| Model | Pooled AUC | Within-night AUC | precision@20 |
|---|---:|---:|---:|
| All features | 0.7487 | 0.7365 | 14.26% |
| Ward-varying features only | 0.7108 | 0.7398 | 14.19% |
| **Prior event count alone** | 0.7060 | **0.7371** | **14.08%** |
| Night-level only (city rain, season) | 0.6147 | **0.5000** | 4.71% |
| Static top-20 | — | — | 14.08% |
| Oracle ceiling | — | — | 37.72% |

Two things to take from this table. A night-level model has within-night AUC of
exactly 0.5 and scores at chance — it cannot order wards at all. And **every
bit of within-night ordering ability comes from prior event count**: adding
twelve features moves within-night AUC by −0.0006.

> **Rule: never report a pooled AUC on a location-day panel as evidence that a
> triage model works.** Report within-night AUC, or precision@k, or both.

### 19.5 The prescribed FMI interaction features do not help either

`docs/01-evaluation-rules.md` argues the headroom must come from memory
interacting with weather, and names `conditional_rate_at_current_band` and
`excess_over_city`. Both are cheap to build from prior data, so they were built
and tested rather than assumed. Rates estimated on the training window only,
Laplace-smoothed toward the citywide rate for each rainfall band:

| Model | Within-night AUC | precision@20 |
|---|---:|---:|
| **prior_n only (memory)** | **0.7371** | **14.08%** |
| prior_n + prior_rank | 0.7369 | 14.08% |
| conditional rate at tonight's band | 0.7091 | 12.94% |
| conditional rate + excess over city | 0.6979 | 12.79% |
| memory + interaction + terrain | 0.7332 | 13.82% |

**All of them are worse than memory alone.** Conditional rate alone loses 1.14
points (Wilcoxon p = 0.041). The cause is visible in the correlations:
`cond_rate` correlates with `prior_n` at **r = 0.853** and `excess` at
**r = 0.877**. Conditioning a ward's history on six rainfall bands splits a
already-thin record into thinner pieces; the estimation noise added exceeds the
interaction signal gained. They are noisier restatements of memory.

The full re-ranking model gains **+0.18 points of the 23.64 available — 0.8% of
the headroom — with Wilcoxon p = 0.84.**

### 19.6 The upper bound: how much of the headroom is ward-level at all?

The decisive test. Rank wards by their event count measured **on the test period
itself** — deliberate leakage, giving perfect foresight of each ward's
propensity. No static per-ward score can beat that, whatever features produced
it: not drainage density, not imperviousness, not land cover.

| | precision@20 |
|---|---:|
| Honest static top-20 (trained to 2023) | 14.08% |
| **Cheating static top-20 (fitted on the test period)** | **15.66%** |
| Oracle with perfect per-night knowledge | 37.72% |

| | Points | Share of headroom |
|---|---:|---:|
| Headroom | 23.64 | 100% |
| **Reachable by a perfect ward-level ranking** | **1.58** | **6.7%** |
| **Irreducibly within-ward / temporal** | **22.06** | **93.3%** |

The cheating list shares 13 of 20 wards with the honest one and beats it by
1.58 points (p = 0.0013) — real, but tiny.

Corroborating evidence that the residual is temporal, not spatial:

- The correlation between consecutive rain nights' event vectors is **0.090**.
  Which wards flood tonight is almost independent of which flooded last time.
- 161 of the 178 non-top-20 wards produced at least one surprise; the 20 most
  surprise-prone hold only 30.8% of them. Surprises are spread thin, not
  concentrated in a knowable set.

### 19.7 The honest read

**The 24 points are not reachable.** Ward-level features are capped at ~1.6 of
them, and we are already within 1.6 of that cap. Rainfall was tested at 9 km
(§17), terrain and elevation here, and the prescribed memory-weather
interactions here. All fail to move precision@20.

What would be needed is per-night, sub-ward information: which drain is blocked
tonight, where the storm cell actually sat, which street reported. None of that
exists in this data, and the complaint label itself is a citizen report rather
than an observed flood, so some of the 22 points is irreducible label noise
rather than missing features.

**This does not invalidate the project — it relocates it.** Consequences:

1. **Triage is a solved-and-bounded problem, and should be presented as one.**
   The static list is within 1.6 points of the best any ward-level ranking can
   do. The honest contribution is not "we beat the list" but "we measured how
   much the list can be beaten, and it is 1.6 points" — with the method that
   establishes it. That is a real finding and it is the kind that does not get
   published often enough.
2. **Proof One needs restating.** As written it is close to unwinnable: nightly
   re-ranking cannot beat a static list by a material margin. What the data
   *does* support is the inverse claim — the event set genuinely moves
   (night-to-night correlation 0.090), so a static list is not capturing a
   stable phenomenon, and yet nothing observable predicts the movement. Stating
   that precisely is more valuable than a marginal precision win would be.
3. **Weight shifts to the Learn outputs.** Emerging detection and intervention
   effectiveness operate on *accumulated* ward history, not on nightly ordering,
   so they are untouched by this result. They are also the more original
   contributions. §12.5's two-target split and the 96 non-register wards as the
   emerging pool are unaffected.
4. **Do not build M3 expecting a precision win.** Build the model ladder to
   *demonstrate* this bound — M0 through M3 all landing near 14% against a
   37.7% ceiling is the result, and the ablation is what makes it credible.

### 19.8 Reproducing this

The analysis is in the session scratchpad rather than the repo, since it is
diagnostic rather than pipeline code. Inputs: `weather_daily` (IFS cells
10–23), `locations`, `data/reference/ward_crosswalk.csv`, and ward elevation
sampled from the Open-Meteo elevation API at each ward centroid plus 12
polygon-boundary points.

Temporal discipline: prior counts for the fit set come from
2020-02-08 → 2022-12-31 and for the test set from 2020-02-08 → 2023-12-31;
models fit on 2023 rain days and evaluated on 2024–25 rain days. The only
exception is §19.6, where leakage is the point.
