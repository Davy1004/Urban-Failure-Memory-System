"""Daily weather aggregation: weather_observations -> weather_daily.

Intensity matters more than totals. 60 mm in one hour floods a road; 60 mm
spread over a day usually does not. So the daily row carries peak-intensity
features alongside the total, plus a soil-saturation proxy.

LEAKAGE
-------
`rain_percentile` and `return_period_yrs` describe how unusual a day's
rainfall is *relative to what was already known at the time*. Both are
therefore computed on an EXPANDING window over strictly earlier dates for
the same cell. Computing them against the full history would leak the
future into every training row and silently invalidate the whole project
(rule 1 in CLAUDE.md).

Concretely: the value written for 2021-06-14 is derived only from
2019-01-01..2021-06-13. The first `min_history_days` days of a cell's
record therefore get NULL rather than a percentile computed from a handful
of neighbours — a wrong number is worse than a missing one.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.base import ingestion_run, resolve_city, upsert_chunk
from app.models.geography import City, WeatherCell
from app.models.observation import WeatherDaily, WeatherObservation

logger = logging.getLogger("ufms.ingestion.weather_daily")

SOURCE_NAME = "UFMS derived — weather_daily"
SOURCE_KW = dict(
    url="",
    licence="derived from Open-Meteo ERA5",
    description=(
        "Daily aggregation of weather_observations. Percentile and return "
        "period use an expanding window over strictly prior dates."
    ),
)

# Below this many prior observations a percentile is noise, so we write NULL.
MIN_HISTORY_DAYS = 365

UPDATE_COLS = [
    "rain_24h_mm", "rain_1h_max_mm", "rain_3h_max_mm", "antecedent_7d_mm",
    "rain_percentile", "return_period_yrs", "season_position",
    "temp_mean_c", "humidity_mean_pct",
]


def _season_position(d: date, start_month: int, end_month: int) -> Optional[int]:
    """Days into the LOCAL monsoon, or None outside it.

    Calendar month is the wrong feature: Bengaluru's season runs Apr-Nov,
    Delhi's Jun-Sep. Normalising to 'days into the local season' is what
    makes the feature mean the same thing in both cities.
    """
    if start_month <= end_month:
        if not (start_month <= d.month <= end_month):
            return None
        season_start = date(d.year, start_month, 1)
    else:  # season wraps the new year
        if not (d.month >= start_month or d.month <= end_month):
            return None
        season_start = date(d.year if d.month >= start_month else d.year - 1,
                            start_month, 1)
    return (d - season_start).days


def _expanding_percentile(values: np.ndarray, min_history: int) -> np.ndarray:
    """Fraction of STRICTLY PRIOR days whose rainfall was <= today's.

    O(n^2) is fine here: a cell holds a few thousand daily rows, and being
    obviously correct matters more than being fast on this one.
    """
    n = len(values)
    out = np.full(n, np.nan)
    for i in range(n):
        if i < min_history:
            continue
        prior = values[:i]                      # strictly earlier — no leakage
        out[i] = float((prior <= values[i]).sum()) / len(prior)
    return out


def _expanding_return_period(values: np.ndarray, min_history: int) -> np.ndarray:
    """Empirical return period in years, from strictly prior days only.

    p = P(daily rain >= today) estimated on prior days; the expected wait
    for such a day is 1/p days, i.e. 1/(p * 365.25) years. When today
    exceeds everything seen before, p is bounded below by 1/(n+1) rather
    than 0 so the result stays finite and honest about its resolution.
    """
    n = len(values)
    out = np.full(n, np.nan)
    for i in range(n):
        if i < min_history:
            continue
        prior = values[:i]
        exceed = int((prior >= values[i]).sum())
        p = max(exceed, 1) / (len(prior) + 1)
        out[i] = 1.0 / (p * 365.25)
    return out


def aggregate_cell(db: Session, cell: WeatherCell, city: City) -> pd.DataFrame:
    """Build the full daily frame for one cell from its hourly rows."""
    rows = db.execute(
        select(
            WeatherObservation.recorded_at,
            WeatherObservation.rainfall_mm,
            WeatherObservation.temperature_c,
            WeatherObservation.humidity_pct,
        )
        .where(WeatherObservation.cell_id == cell.cell_id)
        .order_by(WeatherObservation.recorded_at)
    ).all()
    if not rows:
        return pd.DataFrame()

    h = pd.DataFrame(rows, columns=["recorded_at", "rain", "temp", "humid"])
    for c in ("rain", "temp", "humid"):
        h[c] = pd.to_numeric(h[c], errors="coerce").astype(float)
    h = h.set_index("recorded_at").sort_index()

    # 3-hour peak is computed on the hourly series BEFORE the daily split so
    # a burst that straddles midnight is not sliced in half.
    roll3 = h["rain"].rolling(3, min_periods=1).sum()

    daily = pd.DataFrame({
        "rain_24h_mm": h["rain"].resample("D").sum(min_count=1),
        "rain_1h_max_mm": h["rain"].resample("D").max(),
        "rain_3h_max_mm": roll3.resample("D").max(),
        "temp_mean_c": h["temp"].resample("D").mean(),
        "humidity_mean_pct": h["humid"].resample("D").mean(),
    })
    daily.index = daily.index.date
    daily.index.name = "obs_date"

    # Prior seven days, today excluded — a soil-saturation proxy, and one
    # that must not include today or it stops being 'antecedent'.
    r = daily["rain_24h_mm"].fillna(0.0)
    daily["antecedent_7d_mm"] = r.shift(1).rolling(7, min_periods=1).sum()

    vals = r.to_numpy()
    daily["rain_percentile"] = _expanding_percentile(vals, MIN_HISTORY_DAYS)
    daily["return_period_yrs"] = _expanding_return_period(vals, MIN_HISTORY_DAYS)
    daily["season_position"] = [
        _season_position(d, city.monsoon_start_month, city.monsoon_end_month)
        for d in daily.index
    ]
    return daily


def _to_rows(cell_id: int, daily: pd.DataFrame) -> list[dict]:
    out = []
    for obs_date, r in daily.iterrows():
        def v(name, nd=2):
            x = r[name]
            return None if pd.isna(x) else round(float(x), nd)
        sp = r["season_position"]
        out.append({
            "cell_id": cell_id,
            "obs_date": obs_date,
            "rain_24h_mm": v("rain_24h_mm"),
            "rain_1h_max_mm": v("rain_1h_max_mm"),
            "rain_3h_max_mm": v("rain_3h_max_mm"),
            "antecedent_7d_mm": v("antecedent_7d_mm"),
            "rain_percentile": v("rain_percentile", 5),
            "return_period_yrs": v("return_period_yrs", 3),
            "season_position": None if pd.isna(sp) else int(sp),
            "temp_mean_c": v("temp_mean_c"),
            "humidity_mean_pct": v("humidity_mean_pct"),
        })
    return out


def build_daily(db: Session, city_name: str) -> int:
    """Aggregate every cell of a city. Idempotent — PK(cell_id, obs_date)."""
    city = resolve_city(db, city_name)
    cells = db.execute(
        select(WeatherCell).where(WeatherCell.city_id == city.city_id)
        .order_by(WeatherCell.cell_id)
    ).scalars().all()
    if not cells:
        raise ValueError(
            f"No weather cells for {city.name}. Run the weather loader first."
        )

    total = 0
    with ingestion_run(db, SOURCE_NAME, **SOURCE_KW) as tracker:
        for cell in cells:
            daily = aggregate_cell(db, cell, city)
            if daily.empty:
                logger.warning("cell %s has no hourly rows, skipped", cell.cell_id)
                continue
            rows = _to_rows(cell.cell_id, daily)
            for i in range(0, len(rows), 1000):
                batch = rows[i:i + 1000]
                upsert_chunk(db, WeatherDaily.__table__, batch, UPDATE_COLS)
                tracker.ok(len(batch))
                total += len(batch)
            db.commit()
            logger.info("cell %s: %d daily rows (%s..%s)",
                        cell.cell_id, len(rows), daily.index.min(), daily.index.max())

    logger.info("weather_daily complete for %s: %d rows", city.name, total)
    return total
