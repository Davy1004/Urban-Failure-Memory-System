"""Load BBMP wards and flood-register hotspots into `locations`.

Two populations, deliberately kept apart in one table:

  geom_level='ward'   all 198 BBMP wards, positioned at their POLYGON
                      centroid. This is the analysis unit for everything
                      ward-level, and the population emerging detection
                      scans (Proof Two).
  geom_level='point'  the flood register's own points, one row each,
                      is_known_hotspot=True and hotspot_source naming the
                      KML layer they came from. This is the triage
                      population (Proof One).

Why polygon centroids and not register points: a register point is by
definition a flood-prone spot, so using one as a ward's position drags the
ward toward low ground. That is a systematic bias in every distance and
every nearest-cell assignment, not a missing-data problem. It also only
covers 103 of 198 wards.

The three register layers are loaded WITHOUT merging. They are near-disjoint
(§8.2) and what each represents is not yet established; a dedup threshold is
a decision to document, not a default to pick here.
"""
from __future__ import annotations

import logging
import math
import pathlib
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.base import ingestion_run, resolve_city, upsert_chunk
from app.ingestion.ward_crosswalk import (
    WardCrosswalk, haversine_m, load_crosswalk,
)
from app.models.enums import GeomLevel
from app.models.geography import City, Location, WeatherCell

logger = logging.getLogger("ufms.ingestion.wards")

KML_NS = "{http://www.opengis.net/kml/2.2}"

SOURCE_NAME = "BBMP ward boundaries + flood register"
SOURCE_KW = dict(
    url="https://data.opencity.in/dataset/bbmp-ward-information",
    licence="OpenCity, public domain",
    description=(
        "198-ward BBMP delimitation (bbmp_ward_map_2015.kml) for ward centroids, "
        "plus the three flood-prone-location KML layers as hotspot points."
    ),
)

# The three register layers, in the order §8 describes them.
HOTSPOT_LAYERS = [
    ("flood_vulnerable_map.kml", "BBMP flood-vulnerable locations (KGIS)"),
    ("bbmp_low_lying_areas.kml", "BBMP low-lying areas"),
    ("flood_prone_locations.kml", "BBMP flood-prone locations"),
]

WARD_UPDATE_COLS = ["cell_id", "ward_no", "ward_name", "zone", "latitude",
                    "longitude", "is_known_hotspot", "hotspot_source"]
POINT_UPDATE_COLS = ["cell_id", "ward_no", "ward_name", "zone", "latitude",
                     "longitude", "is_known_hotspot", "hotspot_source"]


def _cells(db: Session, city: City) -> List[Tuple[int, float, float]]:
    rows = db.execute(
        select(WeatherCell.cell_id, WeatherCell.latitude, WeatherCell.longitude)
        .where(WeatherCell.city_id == city.city_id)
        .order_by(WeatherCell.cell_id)
    ).all()
    return [(int(c), float(la), float(lo)) for c, la, lo in rows]


def nearest_cell(lat: float, lon: float,
                 cells: Sequence[Tuple[int, float, float]]) -> Optional[int]:
    if not cells:
        return None
    return min(cells, key=lambda t: haversine_m(lat, lon, t[1], t[2]))[0]


def load_wards(db: Session, city_name: str = "Bengaluru",
               crosswalk: Optional[WardCrosswalk] = None) -> int:
    """One `locations` row per BBMP ward, positioned at its polygon centroid."""
    city = resolve_city(db, city_name)
    cw = crosswalk or load_crosswalk()
    cells = _cells(db, city)
    if not cells:
        raise ValueError(
            f"No weather cells for {city.name}. Run the weather loader first."
        )

    rows = []
    for m in cw:
        if not m.has_centroid:
            logger.warning("ward %r has no centroid, skipped", m.complaint_ward_name)
            continue
        rows.append({
            "city_id": city.city_id,
            "cell_id": nearest_cell(m.centroid_lat, m.centroid_lon, cells),
            # area_name is the COMPLAINT spelling: it is the join key the
            # grievance feed actually uses.
            "area_name": m.complaint_ward_name,
            "ward_no": str(m.bbmp_ward_no) if m.has_ward_no else None,
            "ward_name": m.bbmp_ward_name,
            "zone": m.bbmp_zone,
            "latitude": round(m.centroid_lat, 6),
            "longitude": round(m.centroid_lon, 6),
            "geom_level": GeomLevel.WARD.value,
            # A ward is not itself a hotspot; the register's points are.
            "is_known_hotspot": False,
            "hotspot_source": None,
        })

    with ingestion_run(db, SOURCE_NAME, **SOURCE_KW) as tracker:
        for i in range(0, len(rows), 500):
            batch = rows[i:i + 500]
            upsert_chunk(db, Location.__table__, batch, WARD_UPDATE_COLS)
            tracker.ok(len(batch))
        db.commit()
    logger.info("loaded %d ward locations for %s", len(rows), city.name)
    return len(rows)


def _parse_layer(path: pathlib.Path) -> List[dict]:
    root = ET.parse(path).getroot()
    out = []
    for pm in root.iter(f"{KML_NS}Placemark"):
        d = {}
        nm = pm.find(f"{KML_NS}name")
        if nm is not None and nm.text:
            d["name"] = nm.text.strip()
        for sd in pm.iter(f"{KML_NS}SimpleData"):
            d[sd.get("name")] = (sd.text or "").strip()
        pt = pm.find(f".//{KML_NS}Point/{KML_NS}coordinates")
        if pt is not None and pt.text:
            parts = pt.text.strip().split(",")
            if len(parts) >= 2:
                try:
                    lon, lat = float(parts[0]), float(parts[1])
                except ValueError:
                    lon = lat = float("nan")
                # bbmp_low_lying_areas.kml stores a literal "nan,nan" for one
                # placemark, so float() succeeds and a None check would miss it.
                if not (math.isnan(lon) or math.isnan(lat)):
                    d["lon"], d["lat"] = lon, lat
        out.append(d)
    return out


def load_hotspots(db: Session, raw_dir: pathlib.Path,
                  city_name: str = "Bengaluru") -> int:
    """One `locations` row per register point. Layers are NOT merged."""
    city = resolve_city(db, city_name)
    cells = _cells(db, city)
    rows, skipped = [], 0

    for filename, source_label in HOTSPOT_LAYERS:
        path = raw_dir / filename
        if not path.exists():
            logger.warning("hotspot layer %s not present, skipped", filename)
            continue
        for i, d in enumerate(_parse_layer(path), 1):
            lat, lon = d.get("lat"), d.get("lon")
            if lat is None or lon is None:
                skipped += 1
                logger.warning("%s row %d (%r) has no coordinates, skipped",
                               filename, i, d.get("name") or d.get("LocationName"))
                continue
            label = (d.get("LocationName") or d.get("name") or f"{path.stem} {i}").strip()
            ward_no = d.get("WARDNO")
            rows.append({
                "city_id": city.city_id,
                "cell_id": nearest_cell(lat, lon, cells),
                # Layer-qualified so two layers cannot collide on the unique
                # key, and so provenance survives in the row itself.
                "area_name": f"{label} [{path.stem}#{d.get('OBJECTID', i)}]"[:200],
                "ward_no": str(int(float(ward_no))) if ward_no else None,
                "ward_name": d.get("WARD_NAME") or None,
                "zone": d.get("ZONE") or None,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "geom_level": GeomLevel.POINT.value,
                "is_known_hotspot": True,
                "hotspot_source": source_label,
            })

    with ingestion_run(db, SOURCE_NAME, **SOURCE_KW) as tracker:
        for i in range(0, len(rows), 500):
            batch = rows[i:i + 500]
            upsert_chunk(db, Location.__table__, batch, POINT_UPDATE_COLS)
            tracker.ok(len(batch))
        if skipped:
            tracker.bad(skipped, "no coordinates")
        db.commit()
    logger.info("loaded %d hotspot points (%d skipped for missing coordinates)",
                len(rows), skipped)
    return len(rows)
