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
