"""Open-Meteo historical weather loader (ERA5 reanalysis).

Free, no API key, global, hourly, 1940 to roughly five days ago.
Docs: https://open-meteo.com/en/docs/historical-weather-api

Weather is stored per GRID CELL, not per location. A city needs only a few
cells, which is what keeps six years of hourly data inside a 1 GB free tier.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Iterable, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ingestion.base import ingestion_run, resolve_city, upsert_chunk
from app.models.geography import City, WeatherCell
from app.models.observation import WeatherObservation

logger = logging.getLogger("ufms.ingestion.weather")

SOURCE_NAME = "Open-Meteo Historical Weather API"
SOURCE_KW = dict(
    url="https://archive-api.open-meteo.com/v1/archive",
    licence="CC-BY 4.0 (free for non-commercial use)",
    description="ERA5 reanalysis, hourly, 1940-present. No API key required.",
)

# Open-Meteo serves several reanalyses through the same endpoint. They differ
# in native resolution, which is what decides whether a city the size of
# Bengaluru gets one rainfall series or several (profile §17).
#
#   era5       ~25-31 km. 3 distinct cells over BBMP. The original choice.
#   ecmwf_ifs  ~9 km, 2017-present. 14 distinct cells over BBMP. Current.
#   era5_land  ~11 km, but Open-Meteo returns NULL precipitation for it here,
#              so it is unusable for this project however fine its grid is.
MODELS = {
    "era5": dict(
        source="Open-Meteo ERA5 reanalysis",
        description="ERA5 reanalysis, ~25 km, hourly, 1940-present.",
    ),
    "ecmwf_ifs": dict(
        source="Open-Meteo ECMWF IFS reanalysis",
        description="ECMWF IFS, ~9 km, hourly, 2017-present.",
    ),
    "era5_land": dict(
        source="Open-Meteo ERA5-Land reanalysis",
        description="ERA5-Land, ~11 km. NOTE: precipitation returns NULL.",
    ),
}
DEFAULT_MODEL = "ecmwf_ifs"

# The 14 native ECMWF-IFS grid cells that the 198 BBMP ward centroids snap to.
# Using the model's own cell centres avoids resampling its grid onto ours.
# Derived once by asking the archive API to echo the snapped coordinate for
# each ward centroid; see profile §17.1.
IFS_CELLS = [
    (12.829530, 77.586210),
    (12.899820, 77.493190), (12.899820, 77.574930), (12.899820, 77.656670),
    (12.970120, 77.481810), (12.970120, 77.563640), (12.970120, 77.645450),
    (12.970120, 77.727270),
    (13.040420, 77.470430), (13.040420, 77.552320), (13.040420, 77.634220),
    (13.040420, 77.716110),
    (13.110720, 77.540990), (13.110720, 77.622950),
]


def source_for(model: str) -> tuple[str, dict]:
    """data_sources name + kwargs for a model, so provenance is per-model."""
    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}; expected one of {sorted(MODELS)}")
    m = MODELS[model]
    kw = dict(SOURCE_KW)
    kw["description"] = m["description"] + " Via the Open-Meteo archive API."
    return m["source"], kw

HOURLY_VARS = [
    "precipitation",
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
]

# ERA5 lags real time by roughly five days.
ARCHIVE_LAG_DAYS = 6


def default_cells_for(city: City) -> list[tuple[float, float]]:
    """A small grid around the city centre.

    ERA5 is ~25 km, so a 3x3 grid at 0.2 degrees covers a metro area with
    real spatial variation without exploding the row count.
    """
    lat, lng = float(city.centroid_lat), float(city.centroid_lng)
    step = 0.2
    return [
        (round(lat + i * step, 4), round(lng + j * step, 4))
        for i in (-1, 0, 1)
        for j in (-1, 0, 1)
    ]


def ensure_cells(db: Session, city: City,
                 coords: Optional[Iterable[tuple[float, float]]] = None) -> list[WeatherCell]:
    """Create the city's grid cells if they don't exist yet."""
    coords = list(coords) if coords is not None else default_cells_for(city)
    cells: list[WeatherCell] = []
    for lat, lng in coords:
        cell = db.execute(
            select(WeatherCell).where(
                WeatherCell.latitude == lat, WeatherCell.longitude == lng
            )
        ).scalar_one_or_none()
        if cell is None:
            cell = WeatherCell(city_id=city.city_id, latitude=lat, longitude=lng)
            db.add(cell)
            db.flush()
            logger.info("created weather cell (%s, %s) for %s", lat, lng, city.name)
        cells.append(cell)
    db.commit()
    return cells


def fetch_hourly(lat: float, lng: float, start: date, end: date,
                 timezone_name: str = "Asia/Kolkata",
                 max_retries: int = 4, model: Optional[str] = None) -> dict:
    """One archive request with exponential backoff.

    Open-Meteo rate-limits generously but does throttle; a 429 is not an
    error to give up on, it is an error to wait through.
    """
    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(HOURLY_VARS),
        "timezone": timezone_name,
    }
    if model:
        params["models"] = model
    delay = 2.0
    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = httpx.get(settings.open_meteo_archive_url, params=params, timeout=90.0)
            if resp.status_code == 429:
                raise httpx.HTTPStatusError("rate limited", request=resp.request, response=resp)
            resp.raise_for_status()
            payload = resp.json()
            if "hourly" not in payload:
                raise ValueError(f"unexpected response shape: {list(payload)[:6]}")
            return payload
        except Exception as exc:  # noqa: BLE001 - retry on anything transient
            last_error = exc
            if attempt == max_retries:
                break
            logger.warning("open-meteo attempt %d/%d failed (%s); retrying in %.0fs",
                           attempt, max_retries, exc, delay)
            time.sleep(delay)
            delay *= 2

    raise RuntimeError(
        f"Open-Meteo failed for ({lat}, {lng}) {start}..{end} after "
        f"{max_retries} attempts: {last_error}"
    ) from last_error


def _rows_from_payload(cell_id: int, payload: dict, source_id: Optional[int]) -> list[dict]:
    hourly = payload["hourly"]
    times = hourly.get("time", [])
    precip = hourly.get("precipitation") or [None] * len(times)
    temp = hourly.get("temperature_2m") or [None] * len(times)
    humid = hourly.get("relative_humidity_2m") or [None] * len(times)
    wind = hourly.get("wind_speed_10m") or [None] * len(times)

    rows = []
    for i, ts in enumerate(times):
        rows.append({
            "cell_id": cell_id,
            "recorded_at": datetime.fromisoformat(ts),
            "rainfall_mm": precip[i],
            "temperature_c": temp[i],
            "humidity_pct": humid[i],
            "wind_speed_ms": wind[i],
            "source_id": source_id,
        })
    return rows


def load_weather(db: Session, city_name: str, start: date,
                 end: Optional[date] = None, chunk_years: int = 2,
                 model: str = DEFAULT_MODEL,
                 coords: Optional[Iterable[tuple[float, float]]] = None) -> int:
    """Fetch and upsert hourly weather for every cell of a city.

    Requests are chunked by year to keep responses a sane size. Re-running
    is safe: UNIQUE(cell_id, recorded_at) turns repeats into no-op updates.
    """
    city = resolve_city(db, city_name)
    end = end or (date.today() - timedelta(days=ARCHIVE_LAG_DAYS))
    if end >= date.today() - timedelta(days=ARCHIVE_LAG_DAYS - 1):
        end = date.today() - timedelta(days=ARCHIVE_LAG_DAYS)
        logger.info("clamped end date to %s (ERA5 archive lag)", end)
    if start > end:
        raise ValueError(f"start {start} is after the latest available date {end}")

    cells = ensure_cells(db, city, coords)
    total = 0
    source_name, source_kw = source_for(model)

    with ingestion_run(db, source_name, **source_kw) as tracker:
        source_id = tracker.run.source_id

        for cell in cells:
            window_start = start
            while window_start <= end:
                window_end = min(
                    date(window_start.year + chunk_years, 1, 1) - timedelta(days=1),
                    end,
                )
                logger.info("cell %s (%s, %s): %s..%s",
                            cell.cell_id, cell.latitude, cell.longitude,
                            window_start, window_end)

                payload = fetch_hourly(
                    float(cell.latitude), float(cell.longitude),
                    window_start, window_end, city.timezone, model=model,
                )
                rows = _rows_from_payload(cell.cell_id, payload, source_id)

                for i in range(0, len(rows), 2000):
                    batch = rows[i:i + 2000]
                    upsert_chunk(
                        db, WeatherObservation.__table__, batch,
                        ["rainfall_mm", "temperature_c", "humidity_pct",
                         "wind_speed_ms", "source_id"],
                    )
                    tracker.ok(len(batch))
                    total += len(batch)
                db.commit()

                window_start = window_end + timedelta(days=1)
                time.sleep(0.5)  # be polite to a free service

    logger.info("weather load complete for %s (%s): %d hourly rows",
                city.name, model, total)
    return total
