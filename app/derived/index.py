"""`ward_quarter_index` — the relative flooding index per ward-quarter.

    rel(w,q) = [events(w,q) + s] / [complaints(w,q) * city_share(q) + s]

`events` is a count of distinct ward-DAYS carrying a strict waterlogging
complaint, not a count of complaints: two people reporting the same flooded
junction is one event. `complaints` is the ward's total across every category,
which `complaints` cannot supply because rule 7 forbids loading the rest — it
comes from `ward_period_totals`.

`city_share` is the citywide numerator over the citywide denominator for that
quarter, and it is the whole point of the design. Benchmarking a ward against
zero instead of against the city scored diverging-upward wards as declining,
because the citywide share itself fell 22% over the window (profile §23.1).

The arithmetic is done in float and stored at 16 decimal places, because the
published panel was computed in numpy and the reconciliation test compares the
two at 1e-9.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.derived import INDEX_END, INDEX_START, SMOOTHING
from app.ingestion.base import resolve_city, upsert_chunk
from app.ingestion.bbmp_complaints import load_hazard_map
from app.models.derived import WardQuarterIndex
from app.models.enums import GeomLevel, PeriodType
from app.models.observation import WardPeriodTotal

logger = logging.getLogger("ufms.derived.index")


def strict_event_sub_categories() -> List[str]:
    """The sub-categories that count as a flooding EVENT, not maintenance.

    The strict/broad split is the hazard YAML's, and it is load-bearing:
    `Road side drains` is 66% of the broad label and lifts only 1.33x on rain
    days — a request to clean a drain, filed on any dry Tuesday (profile §12.4).
    """
    hz = load_hazard_map()
    return sorted(
        sub for sub, (code, severity) in hz.by_sub_category.items()
        if code == "WATERLOG" and severity == "event"
    )


def event_days_by_ward_quarter(db: Session, city_id: int) -> pd.DataFrame:
    """Distinct ward-days with a strict event, bucketed into quarters.

    Returns columns `location_id`, `period_start`, `event_days`.
    """
    subs = strict_event_sub_categories()
    placeholders = ", ".join(f":s{i}" for i in range(len(subs)))
    rows = db.execute(
        text(
            "SELECT c.location_id AS location_id, DATE(c.reported_at) AS d "
            "FROM complaints c "
            "JOIN locations l ON l.location_id = c.location_id "
            "WHERE l.city_id = :city AND l.geom_level = :level "
            f"  AND c.sub_category IN ({placeholders}) "
            "  AND c.reported_at >= :start AND c.reported_at < :end "
            "GROUP BY c.location_id, DATE(c.reported_at)"
        ),
        {"city": city_id, "level": GeomLevel.WARD.value,
         "start": INDEX_START, "end": INDEX_END,
         **{f"s{i}": s for i, s in enumerate(subs)}},
    ).all()

    if not rows:
        return pd.DataFrame(columns=["location_id", "period_start", "event_days"])

    ev = pd.DataFrame(rows, columns=["location_id", "d"])
    ev["period_start"] = pd.to_datetime(ev["d"]).dt.to_period("Q").dt.start_time
    return (ev.groupby(["location_id", "period_start"]).size()
              .reset_index(name="event_days"))


def _denominators(db: Session, city_id: int) -> pd.DataFrame:
    rows = db.execute(
        select(WardPeriodTotal.location_id, WardPeriodTotal.period_start,
               WardPeriodTotal.total_complaints)
        .where(WardPeriodTotal.period_type == PeriodType.QUARTER,
               WardPeriodTotal.period_start >= INDEX_START,
               WardPeriodTotal.period_start < INDEX_END)
    ).all()
    tot = pd.DataFrame(rows, columns=["location_id", "period_start", "total_complaints"])
    if tot.empty:
        raise ValueError(
            "ward_period_totals is empty for the index window. Run "
            "`python -m app.ingestion.cli complaints --totals` first: the index "
            "denominator is the ward's complaints across ALL categories, which "
            "`complaints` does not hold."
        )
    tot["period_start"] = pd.to_datetime(tot["period_start"])
    # Only wards this city actually has locations for.
    loc_ids = set(db.execute(
        text("SELECT location_id FROM locations WHERE city_id = :c AND geom_level = :g"),
        {"c": city_id, "g": GeomLevel.WARD.value},
    ).scalars().all())
    return tot[tot["location_id"].isin(loc_ids)].reset_index(drop=True)


def compute_index(db: Session, city_id: int,
                  smoothing: float = SMOOTHING) -> pd.DataFrame:
    """The panel, as a frame. Separated from the write so tests can read it."""
    tot = _denominators(db, city_id)
    ev = event_days_by_ward_quarter(db, city_id)

    panel = tot.merge(ev, on=["location_id", "period_start"], how="left")
    panel["event_days"] = panel["event_days"].fillna(0).astype(int)

    city = (panel.groupby("period_start")
                 .apply(lambda g: g["event_days"].sum() / g["total_complaints"].sum(),
                        include_groups=False)
                 .rename("city_share"))
    panel = panel.merge(city, left_on="period_start", right_index=True)

    expected = panel["total_complaints"] * panel["city_share"]
    panel["smoothing"] = smoothing
    panel["rel_index"] = (panel["event_days"] + smoothing) / (expected + smoothing)
    return panel.sort_values(["location_id", "period_start"]).reset_index(drop=True)


def build_index(db: Session, city_name: str = "Bengaluru",
                smoothing: float = SMOOTHING) -> int:
    """Recompute and upsert `ward_quarter_index`. Idempotent."""
    city = resolve_city(db, city_name)
    panel = compute_index(db, city.city_id, smoothing)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = [
        {"location_id": int(r.location_id),
         "period_type": PeriodType.QUARTER.value,
         "period_start": r.period_start.date(),
         "event_days": int(r.event_days),
         "total_complaints": int(r.total_complaints),
         # repr() round-trips a float exactly, so the stored decimal is the
         # computed value rather than a re-parse of a shortened string.
         "city_share": Decimal(repr(r.city_share)),
         "smoothing": Decimal(repr(r.smoothing)),
         "rel_index": Decimal(repr(r.rel_index)),
         "computed_at": now}
        for r in panel.itertuples(index=False)
    ]
    n = upsert_chunk(db, WardQuarterIndex.__table__, rows,
                     ["event_days", "total_complaints", "city_share",
                      "smoothing", "rel_index", "computed_at"])
    db.commit()
    logger.info("ward_quarter_index: %d ward-quarter rows upserted (%d wards, "
                "%d quarters)", n, panel["location_id"].nunique(),
                panel["period_start"].nunique())
    return n


def read_index(db: Session, city_id: Optional[int] = None) -> pd.DataFrame:
    """The stored index as a wide frame: rows are wards, columns are quarters.

    Every downstream screen reads the index through this, so there is exactly
    one place where a ward-quarter matrix is assembled.
    """
    stmt = (
        "SELECT q.location_id, l.area_name, q.period_start, q.event_days, "
        "       q.total_complaints, q.city_share, q.rel_index "
        "FROM ward_quarter_index q "
        "JOIN locations l ON l.location_id = q.location_id "
        "WHERE q.period_type = :pt"
    )
    params: Dict[str, object] = {"pt": PeriodType.QUARTER.value}
    if city_id is not None:
        stmt += " AND l.city_id = :city"
        params["city"] = city_id
    rows = db.execute(text(stmt), params).all()
    if not rows:
        raise ValueError(
            "ward_quarter_index is empty. Run `python -m app.ingestion.cli "
            "derive` before building anything that reads it."
        )
    df = pd.DataFrame(rows, columns=["location_id", "area_name", "period_start",
                                     "event_days", "total_complaints",
                                     "city_share", "rel_index"])
    df["period_start"] = pd.to_datetime(df["period_start"])
    for col in ("city_share", "rel_index"):
        df[col] = df[col].astype(float)
    return df


def pivot(df: pd.DataFrame, value: str) -> pd.DataFrame:
    """Wards x quarters, indexed by location_id and sorted by period."""
    return df.pivot(index="location_id", columns="period_start", values=value).sort_index(axis=1)


def ward_names(df: pd.DataFrame) -> Dict[int, str]:
    return dict(df.drop_duplicates("location_id")[["location_id", "area_name"]].values)


def quarters(df: pd.DataFrame) -> List[pd.Timestamp]:
    return sorted(df["period_start"].unique())


def quarter_label(ts) -> str:
    """'2020Q2' — the form the reference CSVs and the paper both use."""
    return str(pd.Timestamp(ts).to_period("Q"))


def split_halves(qs: List[pd.Timestamp]) -> Tuple[List, List]:
    """First and second half of the window, first half taking the odd quarter."""
    mid = (len(qs) + 1) // 2
    return qs[:mid], qs[mid:]
