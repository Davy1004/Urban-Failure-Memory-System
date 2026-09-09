"""`watchlist_snapshots` / `watchlist_entries` — the standing top-k list.

The list itself is trivial: rank wards by how many strict event-days they have
had up to a freeze date, take the top k, never re-rank. That is what an officer
already does, and re-ranking it daily on three further years of history moves
precision@20 by 0.15 points (profile §14.3). The list is not the interesting
part.

The interesting part is the three numbers stored beside it. Precision@20 of
14.08% reads as a failure in isolation. Against a random floor of 4.79% and an
oracle ceiling of 37.72% — the ceiling exists because a median rain night
carries about 6 strict events citywide, so 20 slots cannot all be right — it is
37% of everything achievable. The screen must show all three or it invites the
misreading this project spent six sessions disproving.

A rain day is a day whose CITY-MEAN daily rainfall over the model's cells
clears 2.5 mm. Per-ward rainfall was tested at both ~25 km and ~9 km and is
worse, not better (profile §16, §17): restricting the candidate pool to
individually-wet wards costs 6% of precision@20. Quote the city-mean figures
without apology.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.derived import (
    RAIN_MODEL, RAIN_THRESHOLD_MM, WATCHLIST_AS_OF, WATCHLIST_K,
    WATCHLIST_TEST_END, WATCHLIST_TEST_START, WATCHLIST_TRAIN_START,
)
from app.derived.index import strict_event_sub_categories
from app.ingestion.base import resolve_city
from app.models.derived import WatchlistEntry, WatchlistSnapshot
from app.models.enums import GeomLevel, WeatherModel
from app.models.geography import FailureType

logger = logging.getLogger("ufms.derived.watchlist")


def _event_days(db: Session, city_id: int, start: date, end: date) -> pd.DataFrame:
    """Distinct (ward, day) pairs with a strict event, inclusive of both bounds."""
    subs = strict_event_sub_categories()
    placeholders = ", ".join(f":s{i}" for i in range(len(subs)))
    rows = db.execute(
        text(
            "SELECT c.location_id AS location_id, DATE(c.reported_at) AS d "
            "FROM complaints c "
            "JOIN locations l ON l.location_id = c.location_id "
            "WHERE l.city_id = :city AND l.geom_level = :level "
            f"  AND c.sub_category IN ({placeholders}) "
            "  AND DATE(c.reported_at) BETWEEN :start AND :end "
            "GROUP BY c.location_id, DATE(c.reported_at)"
        ),
        {"city": city_id, "level": GeomLevel.WARD.value, "start": start, "end": end,
         **{f"s{i}": s for i, s in enumerate(subs)}},
    ).all()
    df = pd.DataFrame(rows, columns=["location_id", "d"])
    if not df.empty:
        df["d"] = pd.to_datetime(df["d"])
    return df


def rain_days(db: Session, city_id: int, start: date, end: date,
              threshold_mm: float = RAIN_THRESHOLD_MM,
              model: str = RAIN_MODEL) -> List[pd.Timestamp]:
    """Days whose city-mean rainfall over the model's cells clears the threshold."""
    rows = db.execute(
        text(
            "SELECT wd.obs_date AS d, AVG(wd.rain_24h_mm) AS mm "
            "FROM weather_daily wd "
            "JOIN weather_cells wc ON wc.cell_id = wd.cell_id "
            "WHERE wc.city_id = :city AND wc.model = :model "
            "  AND wd.obs_date BETWEEN :start AND :end "
            "GROUP BY wd.obs_date HAVING AVG(wd.rain_24h_mm) >= :thr"
        ),
        {"city": city_id, "model": model, "start": start, "end": end,
         "thr": threshold_mm},
    ).all()
    return sorted(pd.Timestamp(r.d) for r in rows)


def _ward_count(db: Session, city_id: int) -> int:
    return int(db.execute(
        text("SELECT COUNT(*) FROM locations WHERE city_id = :c AND geom_level = :g"),
        {"c": city_id, "g": GeomLevel.WARD.value},
    ).scalar_one())


def score_watchlist(top_ids: List[int], events: pd.DataFrame,
                    days: List[pd.Timestamp], n_wards: int,
                    k: int) -> Dict[str, float]:
    """precision@k for the frozen list, plus the ceiling and the floor.

    All three are means over nights of a per-night precision, never a pooled
    ratio — precision@k only ever compares wards *within* one night, which is
    the whole point of the pooled-AUC rule in the evaluation rules.

    The random floor is the expectation rather than one simulated draw: k wards
    sampled without replacement from n catch k * (events/n) in expectation, so
    the per-night precision is events/n exactly.
    """
    if not days:
        raise ValueError("no held-out rain days to score against")
    by_day = events.groupby("d")["location_id"].apply(set) if not events.empty else pd.Series(dtype=object)
    frozen = set(top_ids)
    hits, sizes = [], []
    for d in days:
        tonight = by_day.get(d, set())
        hits.append(len(tonight & frozen))
        sizes.append(len(tonight))
    n = len(days)
    return {
        "precision_at_k": sum(hits) / n / k,
        "oracle_at_k": sum(min(s, k) for s in sizes) / n / k,
        "random_at_k": sum(sizes) / n / n_wards,
        "test_rain_days": n,
        "test_events": sum(sizes),
    }


def build_watchlist(db: Session, city_name: str = "Bengaluru",
                    as_of: date = WATCHLIST_AS_OF,
                    k: int = WATCHLIST_K,
                    train_start: date = WATCHLIST_TRAIN_START,
                    test_start: Optional[date] = WATCHLIST_TEST_START,
                    test_end: Optional[date] = WATCHLIST_TEST_END,
                    failure_code: str = "WATERLOG") -> int:
    """Freeze a top-k list at `as_of` and score it on the held-out window.

    Pass `test_start=None` for an operational snapshot with no held-out period.
    The three metric columns are then left NULL rather than filled with figures
    borrowed from another snapshot.
    """
    city = resolve_city(db, city_name)
    ftype = db.execute(
        select(FailureType).where(FailureType.code == failure_code)
    ).scalar_one()

    train = _event_days(db, city.city_id, train_start, as_of)
    if train.empty:
        raise ValueError(f"no strict events between {train_start} and {as_of}")

    # Ties broken by area name so two runs produce the same order. Bilekahalli
    # and Jakkur both sit on 64 prior events at the 2023 freeze.
    names = dict(db.execute(
        text("SELECT location_id, area_name FROM locations WHERE city_id = :c"),
        {"c": city.city_id},
    ).all())
    counts = train.groupby("location_id").size().rename("prior_events").reset_index()
    counts["area_name"] = counts["location_id"].map(names)
    counts = counts.sort_values(["prior_events", "area_name"],
                                ascending=[False, True]).reset_index(drop=True)
    top = counts.head(k)

    metrics: Dict[str, object] = {
        "test_rain_days": None, "test_events": None, "precision_at_k": None,
        "oracle_at_k": None, "random_at_k": None,
    }
    per_ward_test: Dict[int, int] = {}
    if test_start is not None and test_end is not None:
        days = rain_days(db, city.city_id, test_start, test_end)
        test_ev = _event_days(db, city.city_id, test_start, test_end)
        if not test_ev.empty:
            test_ev = test_ev[test_ev["d"].isin(set(days))]
            per_ward_test = test_ev.groupby("location_id").size().to_dict()
        metrics = score_watchlist(top["location_id"].tolist(), test_ev, days,
                                  _ward_count(db, city.city_id), k)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    snap = db.execute(
        select(WatchlistSnapshot).where(
            WatchlistSnapshot.city_id == city.city_id,
            WatchlistSnapshot.failure_type_id == ftype.failure_type_id,
            WatchlistSnapshot.as_of_date == as_of,
            WatchlistSnapshot.k == k,
        )
    ).scalar_one_or_none()
    if snap is None:
        snap = WatchlistSnapshot(city_id=city.city_id,
                                 failure_type_id=ftype.failure_type_id,
                                 as_of_date=as_of, k=k)
        db.add(snap)
    snap.train_start = train_start
    snap.test_start = test_start
    snap.test_end = test_end
    snap.rain_threshold_mm = Decimal(str(RAIN_THRESHOLD_MM)) if test_start else None
    snap.weather_model = WeatherModel(RAIN_MODEL) if test_start else None
    snap.test_rain_days = metrics["test_rain_days"]
    snap.test_events = metrics["test_events"]
    for col in ("precision_at_k", "oracle_at_k", "random_at_k"):
        value = metrics[col]
        setattr(snap, col, Decimal(repr(value)) if value is not None else None)
    snap.computed_at = now
    db.flush()

    # Rewritten wholesale: a shorter list must not leave stale ranks behind.
    db.execute(text("DELETE FROM watchlist_entries WHERE snapshot_id = :s"),
               {"s": snap.snapshot_id})
    db.add_all([
        WatchlistEntry(snapshot_id=snap.snapshot_id,
                       rank_position=i + 1,
                       location_id=int(r.location_id),
                       prior_events=int(r.prior_events),
                       test_events=per_ward_test.get(int(r.location_id), 0)
                       if test_start else None)
        for i, r in enumerate(top.itertuples(index=False))
    ])
    db.commit()

    logger.info("watchlist snapshot %s: top %d frozen at %s, precision@%d=%s",
                snap.snapshot_id, k, as_of, k, snap.precision_at_k)
    return len(top)
