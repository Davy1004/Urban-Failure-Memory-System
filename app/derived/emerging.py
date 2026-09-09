"""`emerging_watch` — the rank-based detector, and what it actually detects.

Wards are ranked by the Theil-Sen slope of their `rel_index` over the FIRST
half of the window. The flag is a rank cut, not a significance test, and that
is deliberate: Benjamini-Hochberg over all 103 eligible wards leaves zero
survivors at q = 0.05, 0.10 or 0.20, and exactly one — Jakkur — under the
pre-specified off-register pool (profile §23.3). "These nine wards are rising"
is not defensible; "more wards rise than chance allows" is (permutation
p = 0.0010). So the screen shows a ranking with its p-values visible, and the
endpoint refuses to describe a rank as a discovery.

Two things this file exists to prevent.

**Never test a ward trend against zero.** The citywide share fell 22% over the
window, so a ward whose share fell 5% was *diverging upward* and the zero null
scored it as declining — 0 rising / 10 declining, against 9 / 4 under the
correct null (profile §23.1-§23.2). `rel_index` already carries the city
benchmark, so a slope on it is the difference-in-differences quantity.

**The label is `chronically_above_norm`, not `accelerating`.** Slope-flagged
wards end the second half at mean level 1.77 against 1.16 for all eligible
wards (p = 0.0001), and 10 of 10 finish above the city norm. But they do not
significantly exceed their own first-half level (p = 0.23). The detector finds
wards that stay bad, not wards that are getting worse faster, and §25.1 is
where that was measured. `level_delta` is stored so the screen can show the
difference rather than assert it.

Slope persistence across halves is 0.035 and that is NOT evidence of
instability — a ward that deteriorates and then stays bad has a positive first
slope and a flat second one, so genuine emergence produces low slope
correlation by construction. Test level persistence, which is what `half2_level`
is for.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.derived import EMERGING_FLAG_TOP_N, EMERGING_MIN_EVENTS
from app.derived.index import pivot, quarters, read_index, split_halves
from app.ingestion.base import resolve_city, upsert_chunk
from app.ingestion.ward_crosswalk import load_crosswalk
from app.models.derived import CHRONICALLY_ABOVE_NORM, EmergingWatch
from app.models.enums import GeomLevel

logger = logging.getLogger("ufms.derived.emerging")


def theil_sen(y: np.ndarray) -> float:
    """Median pairwise slope per quarter. Robust to the one-off spike quarters
    that a complaint series is full of, which is why it is used over OLS."""
    return float(stats.theilslopes(y, np.arange(len(y)))[0])


def mann_kendall_p(y: np.ndarray) -> float:
    """Two-sided p for monotone trend. Kendall's tau against the time index."""
    return float(stats.kendalltau(np.arange(len(y)), y)[1])


def compute_emerging(db: Session, city_id: int,
                     min_events: int = EMERGING_MIN_EVENTS,
                     flag_top_n: int = EMERGING_FLAG_TOP_N) -> pd.DataFrame:
    df = read_index(db, city_id)
    qs = quarters(df)
    if len(qs) < 4:
        raise ValueError(f"need at least 4 quarters of index, have {len(qs)}")
    h1, h2 = split_halves(qs)

    rel = pivot(df, "rel_index")
    ev = pivot(df, "event_days")

    eligible = ev.sum(axis=1) >= min_events
    if not eligible.any():
        raise ValueError(f"no ward reaches {min_events} event-days over the window")
    rel = rel.loc[eligible[eligible].index]

    out = pd.DataFrame(index=rel.index)
    out["event_days"] = ev.loc[rel.index].sum(axis=1).astype(int)
    out["half1_slope"] = rel[h1].apply(lambda r: theil_sen(r.values), axis=1)
    out["half1_p"] = rel[h1].apply(lambda r: mann_kendall_p(r.values), axis=1)
    out["half1_level"] = rel[h1].mean(axis=1)
    out["half2_level"] = rel[h2].mean(axis=1)
    out["half2_slope"] = rel[h2].apply(lambda r: theil_sen(r.values), axis=1)
    out["level_delta"] = out["half2_level"] - out["half1_level"]
    out["full_slope"] = rel.apply(lambda r: theil_sen(r.values), axis=1)
    out["full_p"] = rel.apply(lambda r: mann_kendall_p(r.values), axis=1)

    # Ties on slope broken by location_id, so a rebuild reproduces the order.
    out = out.sort_values("half1_slope", ascending=False, kind="mergesort")
    out["rank_position"] = np.arange(1, len(out) + 1)
    out["is_flagged"] = out["rank_position"] <= flag_top_n
    out["window_start"] = pd.Timestamp(qs[0])
    out["as_of_date"] = pd.Period(pd.Timestamp(qs[-1]), "Q").end_time.normalize()
    return out.reset_index()


def build_emerging(db: Session, city_name: str = "Bengaluru",
                   min_events: int = EMERGING_MIN_EVENTS,
                   flag_top_n: int = EMERGING_FLAG_TOP_N) -> int:
    city = resolve_city(db, city_name)
    out = compute_emerging(db, city.city_id, min_events, flag_top_n)

    # From the crosswalk, not from `locations.is_known_hotspot`: that flag is
    # set on the 398 register POINTS, so every one of the 198 ward rows carries
    # FALSE even though 102 of those wards are on the register. The crosswalk's
    # `in_flood_register` is the ward-level fact, and it is what the published
    # emerging table (profile §23.2) used.
    crosswalk = load_crosswalk()
    names = dict(db.execute(
        text("SELECT location_id, area_name FROM locations "
             "WHERE city_id = :c AND geom_level = :g"),
        {"c": city.city_id, "g": GeomLevel.WARD.value},
    ).all())
    on_register = {
        loc_id: crosswalk.get(name).in_flood_register
        for loc_id, name in names.items() if name in crosswalk
    }

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = [
        {"location_id": int(r.location_id),
         "as_of_date": r.as_of_date.date(),
         "window_start": r.window_start.date(),
         "rank_position": int(r.rank_position),
         "event_days": int(r.event_days),
         "half1_slope": Decimal(repr(r.half1_slope)),
         "half1_p": Decimal(repr(r.half1_p)),
         "half1_level": Decimal(repr(r.half1_level)),
         "half2_level": Decimal(repr(r.half2_level)),
         "half2_slope": Decimal(repr(r.half2_slope)),
         "level_delta": Decimal(repr(r.level_delta)),
         "full_slope": Decimal(repr(r.full_slope)),
         "full_p": Decimal(repr(r.full_p)),
         "is_flagged": bool(r.is_flagged),
         "on_register": bool(on_register.get(int(r.location_id), False)),
         "label": CHRONICALLY_ABOVE_NORM,
         "computed_at": now}
        for r in out.itertuples(index=False)
    ]
    n = upsert_chunk(db, EmergingWatch.__table__, rows,
                     ["window_start", "rank_position", "event_days",
                      "half1_slope", "half1_p", "half1_level", "half2_level",
                      "half2_slope", "level_delta", "full_slope", "full_p",
                      "is_flagged", "on_register", "label", "computed_at"])
    db.commit()
    logger.info("emerging_watch: %d eligible wards ranked, top %d flagged as %s",
                n, flag_top_n, CHRONICALLY_ABOVE_NORM)
    return n


def level_persistence(db: Session, city_id: int,
                      flag_top_n: int = EMERGING_FLAG_TOP_N) -> dict:
    """Do the flagged wards stay above the city norm? The claim rests on this.

    Reported alongside the list so the screen can state what the detector was
    measured to do rather than what a rising slope suggests it does.
    """
    rows = db.execute(
        text("SELECT e.rank_position, e.half1_level, e.half2_level "
             "FROM emerging_watch e JOIN locations l "
             "  ON l.location_id = e.location_id "
             "WHERE l.city_id = :c"),
        {"c": city_id},
    ).all()
    if not rows:
        raise ValueError("emerging_watch is empty")
    df = pd.DataFrame(rows, columns=["rank_position", "half1_level", "half2_level"])
    df["half1_level"] = df["half1_level"].astype(float)
    df["half2_level"] = df["half2_level"].astype(float)

    flagged = df[df["rank_position"] <= flag_top_n]
    others = df[df["rank_position"] > flag_top_n]
    _, p_vs_others = stats.mannwhitneyu(flagged["half2_level"],
                                        others["half2_level"],
                                        alternative="greater")
    # Does the flag find wards that keep getting worse, or wards that stay bad?
    _, p_vs_self = stats.wilcoxon(flagged["half2_level"], flagged["half1_level"],
                                  alternative="greater")
    return {
        "flagged_n": len(flagged),
        "flagged_half1_level": float(flagged["half1_level"].mean()),
        "flagged_half2_level": float(flagged["half2_level"].mean()),
        "all_half2_level": float(df["half2_level"].mean()),
        "flagged_above_norm": int((flagged["half2_level"] > 1.0).sum()),
        "p_vs_other_wards": float(p_vs_others),
        "p_vs_own_first_half": float(p_vs_self),
    }
