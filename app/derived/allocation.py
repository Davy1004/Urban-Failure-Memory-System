"""`ward_allocation` — the effectiveness screen, which shows ALLOCATION.

**The dose-response is retracted and there is nothing to put in its place.**
The published −0.0240 on log spend (p = 0.0138, n = 110) becomes −0.0064
(p = 0.833) refitted on treated wards only, because `log1p(spend)` placed 7
untreated wards at 0 against every treated ward at 16–20 and the slope was
fitted through two clusters across a 16-unit gap (profile §27.2). Those 7 are
not a valid control group — 5 of them had ₹37–121 M of drainage work before the
window, so "untreated" only ever meant "no work order ending inside an
arbitrary 24-month box" (§28.5). The treated indicator is therefore not a
fallback estimate either.

**And no other design is available.** Zero of 196 wards have their first-ever
drainage work inside the window; all were first treated 2011–2014. Ward work
profiles correlate with the citywide calendar at ρ = +0.505, and the work-order
file stops at 2023Q1 while the outcome panel runs to 2025Q1, so 40% of the
"post" period is censoring rather than absence of treatment. A unit that is
always treated has no before. Analysis is closed (§28).

What this table carries instead is the allocation finding, which is about how
money is distributed and is untouched by any of that:

    Drainage works are distributed continuously and near-uniformly across all
    198 wards and have been since 2013, so no observational evaluation of their
    effect is identifiable from these records — the treatment does not vary
    enough for any design to exploit.

    Spend tracks ward AREA (Spearman +0.474), not relative flooding need
    (+0.082, p = 0.39). It correlates with absolute complaint counts (+0.274)
    because large wards generate more complaints of every kind; controlling for
    area, that correlation vanishes (−0.050, p = 0.60).

`delta_index` is stored because the screen plots spend against it. It is a
description of what happened, not an estimate of what spend did, and
`allocation_summary` deliberately returns no coefficient.
"""
from __future__ import annotations

import logging
import pathlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.derived import (
    ALLOCATION_MIN_EVENTS, ALLOCATION_POST_YEAR, ALLOCATION_PRE_END,
    WORKS_WINDOW_END, WORKS_WINDOW_START,
)
from app.derived.index import pivot, quarters, read_index
from app.derived.work_orders import WORK_ORDER_DIR, load_work_orders
from app.ingestion.base import resolve_city, upsert_chunk
from app.ingestion.ward_crosswalk import load_crosswalk
from app.models.derived import WardAllocation

logger = logging.getLogger("ufms.derived.allocation")


def compute_allocation(db: Session, city_id: int, raw_dir: pathlib.Path,
                       min_events: int = ALLOCATION_MIN_EVENTS) -> pd.DataFrame:
    df = read_index(db, city_id)
    qs = quarters(df)
    pre_q = [q for q in qs if pd.Timestamp(q) < pd.Timestamp(ALLOCATION_PRE_END)]
    post_q = [q for q in qs if pd.Timestamp(q).year >= ALLOCATION_POST_YEAR]
    if not pre_q or not post_q:
        raise ValueError(
            f"index window {qs[0]}..{qs[-1]} does not cover both the pre period "
            f"(before {ALLOCATION_PRE_END}) and the post period "
            f"({ALLOCATION_POST_YEAR} onward)"
        )

    rel = pivot(df, "rel_index")
    ev = pivot(df, "event_days")
    names = df.drop_duplicates("location_id").set_index("location_id")["area_name"]

    panel = pd.DataFrame({
        "area_name": names,
        "pre_index": rel[pre_q].mean(axis=1),
        "post_index": rel[post_q].mean(axis=1),
        "event_days_pre": ev[pre_q].sum(axis=1).astype(int),
        "event_days_post": ev[post_q].sum(axis=1).astype(int),
        # Over the WHOLE window, not pre+post. The targeting check in §26.5
        # asks whether spend follows a ward's absolute complaint volume, and
        # that is the ward's total, not the two windows the design happens to
        # compare. Using pre+post moves the partial correlation from -0.050 to
        # +0.018 and quietly changes the finding.
        "event_days_total": ev.sum(axis=1).astype(int),
    })
    panel["delta_index"] = panel["post_index"] - panel["pre_index"]
    panel = panel[(panel["event_days_pre"] + panel["event_days_post"]) >= min_events]

    crosswalk = load_crosswalk()
    panel["ward_no"] = [crosswalk.ward_no(n) for n in panel["area_name"]]
    panel["ward_area_sqkm"] = [crosswalk.get(n).ward_area_sqkm
                               for n in panel["area_name"]]

    wo_dir = pathlib.Path(raw_dir) / "work_orders"
    works = load_work_orders(wo_dir if wo_dir.exists() else WORK_ORDER_DIR)
    spend = works.spend_by_ward(WORKS_WINDOW_START, WORKS_WINDOW_END)

    panel = panel.reset_index(names="location_id").merge(spend, on="ward_no", how="left")
    panel["drainage_works"] = panel["drainage_works"].fillna(0).astype(int)
    panel["drainage_spend"] = panel["drainage_spend"].fillna(0.0)
    panel["is_treated"] = panel["drainage_spend"] > 0
    return panel.sort_values("area_name").reset_index(drop=True)


def build_allocation(db: Session, raw_dir: pathlib.Path = pathlib.Path("data/raw"),
                     city_name: str = "Bengaluru",
                     min_events: int = ALLOCATION_MIN_EVENTS) -> int:
    city = resolve_city(db, city_name)
    panel = compute_allocation(db, city.city_id, raw_dir, min_events)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = [
        {"location_id": int(r.location_id),
         "window_start": WORKS_WINDOW_START,
         "window_end": WORKS_WINDOW_END,
         "drainage_works": int(r.drainage_works),
         "drainage_spend": Decimal(repr(float(r.drainage_spend))).quantize(Decimal("0.01")),
         "ward_area_sqkm": (Decimal(repr(float(r.ward_area_sqkm)))
                            if r.ward_area_sqkm is not None else None),
         "event_days_pre": int(r.event_days_pre),
         "event_days_post": int(r.event_days_post),
         "event_days_total": int(r.event_days_total),
         "pre_index": Decimal(repr(r.pre_index)),
         "post_index": Decimal(repr(r.post_index)),
         "delta_index": Decimal(repr(r.delta_index)),
         "is_treated": bool(r.is_treated),
         "computed_at": now}
        for r in panel.itertuples(index=False)
    ]
    n = upsert_chunk(db, WardAllocation.__table__, rows,
                     ["drainage_works", "drainage_spend", "ward_area_sqkm",
                      "event_days_pre", "event_days_post", "event_days_total",
                      "pre_index",
                      "post_index", "delta_index", "is_treated", "computed_at"])
    db.commit()
    logger.info("ward_allocation: %d wards, %d treated, total drainage spend "
                "%.0f INR over %s..%s", n, int(panel["is_treated"].sum()),
                panel["drainage_spend"].sum(), WORKS_WINDOW_START, WORKS_WINDOW_END)
    return n


def _partial_spearman(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> tuple:
    """Spearman between x and y with z partialled out, on the ranks.

    The whole targeting objection turns on this one number: spend correlates
    with absolute complaint counts, and the question is whether anything is
    left once ward size is removed.
    """
    rx, ry, rz = (stats.rankdata(v) for v in (x, y, z))
    ex = rx - np.polyval(np.polyfit(rz, rx, 1), rz)
    ey = ry - np.polyval(np.polyfit(rz, ry, 1), rz)
    r, p = stats.pearsonr(ex, ey)
    return float(r), float(p)


def allocation_summary(db: Session, city_id: int) -> Dict[str, object]:
    """The finding, as numbers: what spend tracks and what it does not.

    Returns correlations only. There is deliberately no coefficient on spend
    here — profile §27.2 retracted it and §28 established that no outcome
    design is identifiable on this data.
    """
    rows = db.execute(
        text("SELECT a.location_id, l.area_name, a.drainage_spend, "
             "       a.ward_area_sqkm, a.pre_index, a.post_index, a.delta_index, "
             "       a.event_days_pre, a.event_days_post, a.event_days_total, "
             "       a.is_treated, a.drainage_works "
             "FROM ward_allocation a JOIN locations l "
             "  ON l.location_id = a.location_id "
             "WHERE l.city_id = :c"),
        {"c": city_id},
    ).all()
    if not rows:
        raise ValueError("ward_allocation is empty")

    d = pd.DataFrame(rows, columns=[
        "location_id", "area_name", "spend", "area", "pre", "post", "delta",
        "ev_pre", "ev_post", "events", "is_treated", "works"])
    for col in ("spend", "area", "pre", "post", "delta"):
        d[col] = d[col].astype(float)
    # MySQL BOOLEAN is TINYINT, so this arrives as 0/1 rather than False/True.
    d["is_treated"] = d["is_treated"].astype(bool)

    def sp(a, b):
        r, p = stats.spearmanr(d[a], d[b])
        return {"rho": float(r), "p": float(p)}

    partial_r, partial_p = _partial_spearman(d["spend"].values, d["events"].values,
                                             d["area"].values)
    treated = d[d["is_treated"]]
    return {
        "n_wards": len(d),
        "n_treated": int(d["is_treated"].sum()),
        "n_untreated": int((~d["is_treated"]).sum()),
        "total_spend": float(d["spend"].sum()),
        "median_spend_treated": float(treated["spend"].median()),
        "spend_vs_area": sp("spend", "area"),
        "spend_vs_pre_index": sp("spend", "pre"),
        "spend_vs_absolute_events": sp("spend", "events"),
        "area_vs_absolute_events": sp("area", "events"),
        "spend_vs_events_controlling_area": {"rho": partial_r, "p": partial_p},
    }
