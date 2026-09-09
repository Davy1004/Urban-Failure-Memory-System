"""BBMP grievance loader.

Driven entirely by `data/reference/hazard_categories.yaml`. Nothing about which
complaints count as which hazard is decided here — that file is the definition,
and it is a methodological artifact (profile §10, §12.4).

Three deliberate decisions, each of which would be a bug if reversed:

  * **Matched on `Sub Category`, not `Category`.** 84% of the waterlogging
    signal sits under `Road Maintenance(Engg)`, so a Category filter silently
    drops it while still returning plausible output (profile §10.1).
  * **Timestamps truncated to DATE.** The source is a 12-hour clock with the
    AM/PM marker stripped — no row has hour 0 or 13-23 across 766,648 rows — so
    any time-of-day value would be fiction (profile §6).
  * **Wards absent from the flood register are KEPT.** They are the emerging-
    detection population, not a coverage gap (profile §12.5).

Idempotent on `Complaint ID`, which is globally unique across all six yearly
files with zero collisions (profile §7).
"""
from __future__ import annotations

import logging
import pathlib
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple

import pandas as pd
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.base import ingestion_run, resolve_city, upsert_chunk
from app.ingestion.ward_crosswalk import WardCrosswalk, load_crosswalk
from app.models.enums import ComplaintStatus, GeomLevel
from app.models.geography import FailureType, Location
from app.models.observation import Complaint, WardPeriodTotal

logger = logging.getLogger("ufms.ingestion.complaints")

HAZARD_YAML = (
    pathlib.Path(__file__).resolve().parents[2]
    / "data" / "reference" / "hazard_categories.yaml"
)

SOURCE_NAME = "BBMP Grievances (OpenCity)"
SOURCE_KW = dict(
    url="https://data.opencity.in/dataset/bbmp-grievances-data",
    licence="OpenCity, public domain",
    description=(
        "BBMP citizen grievances 2020-2025, ward level. Filtered at load to "
        "waterlogging and solid waste per data/reference/hazard_categories.yaml."
    ),
)

# The source encodes absence as these literal strings, not as empty cells.
NA_STRINGS = ["", "null", "NON Ward"]

CSV_COLUMNS = ["Complaint ID", "Category", "Sub Category", "Grievance Date",
               "Ward Name", "Grievance Status", "Staff Remarks", "Staff Name"]

DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


@dataclass(frozen=True)
class HazardMap:
    """The parsed YAML. `severity` is the strict/broad split (profile §12.4)."""
    # sub_category -> (failure code, severity) where severity is event|maintenance
    by_sub_category: Dict[str, Tuple[str, str]]
    # category -> failure code, for hazards matched at category level
    by_category: Dict[str, str]
    status_map: Dict[str, ComplaintStatus]
    expected_rows: Dict[str, int] = field(default_factory=dict)

    def classify(self, category: Optional[str],
                 sub_category: Optional[str]) -> Optional[Tuple[str, str]]:
        if sub_category and sub_category in self.by_sub_category:
            return self.by_sub_category[sub_category]
        if category and category in self.by_category:
            return self.by_category[category], "operational"
        return None


def load_hazard_map(path: pathlib.Path = HAZARD_YAML) -> HazardMap:
    if not path.exists():
        raise FileNotFoundError(
            f"hazard map not found at {path}. It is a committed, hand-curated "
            f"artifact; it is not generated at runtime."
        )
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))

    by_sub: Dict[str, Tuple[str, str]] = {}
    w = doc["waterlog"]
    for severity in ("event", "maintenance"):
        for entry in w[severity]:
            s = entry["sub_category"]
            if s in by_sub:
                raise ValueError(f"{s!r} appears twice in the hazard map")
            by_sub[s] = (w["code"], severity)

    g = doc["garbage"]
    by_cat = {g["category"]: g["code"]}

    status = {}
    for src, spec in doc["status_map"].items():
        status[str(src)] = ComplaintStatus(spec["to"])

    expected = {
        "waterlog_event": w["event_total_rows"],
        "waterlog_maintenance": w["maintenance_total_rows"],
        "waterlog_broad": w["broad_total_rows"],
        "garbage": g["total_rows"],
        "source_total": doc["meta"]["total_source_rows"],
    }
    return HazardMap(by_sub, by_cat, status, expected)


def read_csv(path: pathlib.Path) -> pd.DataFrame:
    """One yearly file, with the source's sentinel strings treated as NA."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=NA_STRINGS)
    missing = [c for c in CSV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"{path.name} is missing expected column(s) {missing}. The header "
            f"signature has changed; re-profile before loading (profile §2)."
        )
    return df


def _location_ids(db: Session, city_id: int) -> Dict[str, int]:
    rows = db.execute(
        select(Location.area_name, Location.location_id)
        .where(Location.city_id == city_id,
               Location.geom_level == GeomLevel.WARD)
    ).all()
    return {name: lid for name, lid in rows}


def _failure_type_ids(db: Session) -> Dict[str, int]:
    return {c: i for c, i in db.execute(
        select(FailureType.code, FailureType.failure_type_id)).all()}


def load_complaints(db: Session, raw_dir: pathlib.Path,
                    city_name: str = "Bengaluru",
                    hazard_map: Optional[HazardMap] = None,
                    crosswalk: Optional[WardCrosswalk] = None,
                    batch_size: int = 2000) -> dict:
    """Load every yearly grievance CSV. Returns a report dict."""
    city = resolve_city(db, city_name)
    hz = hazard_map or load_hazard_map()
    cw = crosswalk or load_crosswalk()
    loc_ids = _location_ids(db, city.city_id)
    ft_ids = _failure_type_ids(db)
    if not loc_ids:
        raise ValueError(
            f"No ward locations for {city.name}. Run `cli wards` first."
        )

    files = sorted(raw_dir.glob("bbmp_grievances_*.csv"))
    if not files:
        raise FileNotFoundError(f"no bbmp_grievances_*.csv under {raw_dir}")

    rep = {"files": len(files), "rows_read": 0, "rows_kept": 0,
           "dropped_not_hazard": 0, "dropped_null_ward": 0,
           "dropped_unresolved_ward": 0, "dropped_bad_date": 0,
           "by_severity": {}, "by_code": {}}

    with ingestion_run(db, SOURCE_NAME, **SOURCE_KW) as tracker:
        source_id = tracker.run.source_id
        run_id = tracker.run.run_id

        for path in files:
            df = read_csv(path)
            rep["rows_read"] += len(df)

            cls = [hz.classify(c, s) for c, s in
                   zip(df["Category"], df["Sub Category"])]
            keep = pd.Series([c is not None for c in cls], index=df.index)
            rep["dropped_not_hazard"] += int((~keep).sum())
            df = df[keep].copy()
            df["_code"] = [c[0] for c, k in zip(cls, keep) if k]
            df["_sev"] = [c[1] for c, k in zip(cls, keep) if k]

            null_ward = df["Ward Name"].isna()
            rep["dropped_null_ward"] += int(null_ward.sum())
            df = df[~null_ward]

            unknown = sorted(set(df["Ward Name"]) - set(cw._by_name))
            if unknown:
                raise KeyError(
                    f"{path.name}: {len(unknown)} ward name(s) absent from the "
                    f"crosswalk: {unknown[:5]}. Resolve them by hand in "
                    f"data/reference/ward_crosswalk.csv — do not fuzzy-match."
                )
            excluded = cw.excluded_names
            drop = df["Ward Name"].isin(excluded)
            rep["dropped_unresolved_ward"] += int(drop.sum())
            df = df[~drop]

            when = pd.to_datetime(df["Grievance Date"], format=DATE_FORMAT,
                                  errors="coerce")
            bad = when.isna()
            rep["dropped_bad_date"] += int(bad.sum())
            df, when = df[~bad], when[~bad]
            # DATE, not DATETIME. The source lost its AM/PM marker (profile §6).
            df["_date"] = when.dt.normalize()

            # to_dict rather than itertuples: the source column names contain
            # spaces, which itertuples silently renames.
            rows = []
            for rec in df.to_dict("records"):
                rows.append({
                    "location_id": loc_ids[rec["Ward Name"]],
                    "failure_type_id": ft_ids.get(rec["_code"]),
                    "external_id": str(rec["Complaint ID"]),
                    "reported_at": rec["_date"].to_pydatetime(),
                    "category": rec["Category"],
                    "sub_category": rec["Sub Category"],
                    "status": hz.status_map.get(
                        rec["Grievance Status"], ComplaintStatus.UNKNOWN).value,
                    "description": None,
                    "source_id": source_id,
                    "run_id": run_id,
                })
                rep["by_severity"][rec["_sev"]] = rep["by_severity"].get(rec["_sev"], 0) + 1
                rep["by_code"][rec["_code"]] = rep["by_code"].get(rec["_code"], 0) + 1

            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                upsert_chunk(db, Complaint.__table__, batch,
                             ["location_id", "failure_type_id", "reported_at",
                              "category", "sub_category", "status", "run_id"])
                tracker.ok(len(batch))
            db.commit()
            rep["rows_kept"] += len(rows)
            logger.info("%s: %d of %d rows kept", path.name, len(rows), len(df) + int(bad.sum()))

        tracker.bad(rep["dropped_unresolved_ward"] + rep["dropped_bad_date"])

    logger.info(
        "complaints loaded: %s kept of %s read (%.1f%%); dropped %s non-hazard, "
        "%s null ward, %s unresolved ward, %s unparseable date",
        f"{rep['rows_kept']:,}", f"{rep['rows_read']:,}",
        100 * rep["rows_kept"] / max(rep["rows_read"], 1),
        f"{rep['dropped_not_hazard']:,}", f"{rep['dropped_null_ward']:,}",
        f"{rep['dropped_unresolved_ward']:,}", f"{rep['dropped_bad_date']:,}",
    )
    logger.info("by hazard: %s", rep["by_code"])
    logger.info("by severity: %s", rep["by_severity"])
    return rep


# ---------------------------------------------------------------------------
# The denominator problem
# ---------------------------------------------------------------------------
# The relative flooding index is
#
#     rel(w,q) = events(w,q) / [ all_complaints(w,q) * city_share(q) ]
#
# and its denominator is the ward's TOTAL complaints across every category —
# electrical, roads, everything — not the 237,157-row hazard subset this loader
# keeps. CLAUDE.md rule 7 forbids loading all 766,648 rows, so the database
# alone cannot reproduce the index.
#
# The denominator is a property of the source extract, not of the model, so it
# is persisted as a committed reference artifact: 198 wards x 20 quarters =
# 3,960 rows, diffable, and regenerated by the same pass that reads the CSVs.
#
# It now has a proper home as well: `upsert_ward_period_totals` writes the same
# figures into the `ward_period_totals` table (migration 5fabc9db9f7d), so the
# index is rebuildable from the database alone. The CSV stays as the diffable
# reference copy - it is derived from the source extract, not from the
# database, and a reviewer should be able to see it change in a commit.

TOTALS_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "data" / "reference" / "ward_period_totals.csv"
)


def write_ward_period_totals(raw_dir: pathlib.Path,
                             out: pathlib.Path = TOTALS_PATH,
                             freq: str = "Q") -> pd.DataFrame:
    """Total complaints per ward per period, over ALL categories.

    Reads the raw CSVs rather than the database on purpose: the database holds
    only the hazard subset, and this is the denominator that subset is measured
    against.
    """
    files = sorted(raw_dir.glob("bbmp_grievances_*.csv"))
    if not files:
        raise FileNotFoundError(f"no bbmp_grievances_*.csv under {raw_dir}")
    frames = []
    for p in files:
        d = read_csv(p)[["Ward Name", "Grievance Date"]]
        d = d[d["Ward Name"].notna()]
        d["dt"] = pd.to_datetime(d["Grievance Date"], format=DATE_FORMAT,
                                 errors="coerce")
        frames.append(d.dropna(subset=["dt"]))
    df = pd.concat(frames, ignore_index=True)
    df["period"] = df["dt"].dt.to_period(freq).astype(str)
    tot = (df.groupby(["Ward Name", "period"]).size()
             .reset_index(name="total_complaints")
             .rename(columns={"Ward Name": "ward"})
             .sort_values(["ward", "period"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    tot.to_csv(out, index=False)
    logger.info("wrote %s: %d ward-period rows, %s complaints total",
                out.name, len(tot), f"{int(tot['total_complaints'].sum()):,}")
    return tot


def load_ward_period_totals(path: pathlib.Path = TOTALS_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Regenerate with "
            f"`python -m app.ingestion.cli complaints --totals`."
        )
    return pd.read_csv(path)


def upsert_ward_period_totals(db: Session, city_name: str = "Bengaluru",
                              totals: Optional[pd.DataFrame] = None,
                              path: pathlib.Path = TOTALS_PATH,
                              period_type: str = "quarter") -> int:
    """Put the denominator in the database, keyed on location_id.

    Reads the reference CSV rather than the raw files so that the table and the
    committed artifact cannot disagree: one of them is the source, and it is
    the CSV, because rule 7 forbids the database from ever holding the rows the
    figure is computed from.
    """
    city = resolve_city(db, city_name)
    loc_ids = _location_ids(db, city.city_id)
    tot = totals if totals is not None else load_ward_period_totals(path)

    unknown = sorted(set(tot["ward"]) - set(loc_ids))
    if unknown:
        raise ValueError(
            f"{len(unknown)} ward(s) in {path.name} have no location row: "
            f"{unknown[:5]}. Run `cli wards` first; do not fuzzy-match."
        )

    rows = [
        {"location_id": loc_ids[r.ward],
         "period_type": period_type,
         "period_start": pd.Period(r.period).start_time.date(),
         "total_complaints": int(r.total_complaints)}
        for r in tot.itertuples(index=False)
    ]
    n = upsert_chunk(db, WardPeriodTotal.__table__, rows,
                     ["total_complaints"])
    db.commit()
    logger.info("ward_period_totals: %d rows upserted (%s grain)", n, period_type)
    return n
