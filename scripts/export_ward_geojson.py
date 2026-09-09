"""Export the 198 BBMP ward polygons as GeoJSON for the frontend choropleth.

    python scripts/export_ward_geojson.py

Reads `data/raw/bbmp_ward_map_2015.kml` — the same 198-ward delimitation the
crosswalk was built on, so `ward_no` joins straight onto `locations.ward_no`
and onto every derived table through it. The 2022 KML is a different
delimitation and would not join; do not substitute it.

Two things this does beyond a format conversion:

**It simplifies.** Full-resolution boundaries are ~1.2 MB of KML and the browser
does not need metre-accurate ward edges to shade a choropleth. Coordinates are
rounded to 4 decimal places (~11 m, under one screen pixel at city zoom) and consecutive duplicates dropped, which is
lossless at display scale and roughly halves the payload.

**It refuses to guess.** If a placemark has no ward number, or the file does not
contain exactly 198 wards, it fails loudly rather than shipping a map with holes
in it — a missing ward on a choropleth reads as "no flooding here", which is a
different and worse claim than "no data".
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

KML_NS = "{http://www.opengis.net/kml/2.2}"
ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "bbmp_ward_map_2015.kml"
DEFAULT_OUT = ROOT / "frontend" / "public" / "bbmp-wards.geojson"

N_WARDS = 198
PRECISION = 4           # ~11 m at Bengaluru's latitude; a screen pixel is 20-40 m
                        # at the zoom this map opens at, so this is lossless
                        # on screen and drops a third of the points.
WARD_NO = re.compile(r"(\d+)")


def _ring(text: str) -> list[list[float]]:
    """KML coordinates are 'lon,lat,alt' triples; GeoJSON wants [lon, lat]."""
    out: list[list[float]] = []
    for token in text.split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        point = [round(float(parts[0]), PRECISION), round(float(parts[1]), PRECISION)]
        if not out or out[-1] != point:
            out.append(point)
    if len(out) > 2 and out[0] != out[-1]:
        out.append(out[0])
    return out


def _polygons(placemark: ET.Element) -> list:
    """Every Polygon under a placemark, outer ring plus any holes."""
    polys = []
    for poly in placemark.iter(f"{KML_NS}Polygon"):
        rings = []
        outer = poly.find(f"{KML_NS}outerBoundaryIs/{KML_NS}LinearRing/{KML_NS}coordinates")
        if outer is None or not (outer.text or "").strip():
            continue
        rings.append(_ring(outer.text))
        for inner in poly.findall(
            f"{KML_NS}innerBoundaryIs/{KML_NS}LinearRing/{KML_NS}coordinates"
        ):
            if (inner.text or "").strip():
                rings.append(_ring(inner.text))
        polys.append(rings)
    return polys


def build(source: pathlib.Path = SOURCE) -> dict:
    if not source.exists():
        raise FileNotFoundError(
            f"{source} not found. It is the 198-ward BBMP delimitation the ward "
            f"crosswalk was built on; the choropleth cannot be drawn without it."
        )
    root = ET.parse(source).getroot()

    features = []
    seen: set[int] = set()
    for pm in root.iter(f"{KML_NS}Placemark"):
        name_el = pm.find(f"{KML_NS}name")
        name = (name_el.text or "").strip() if name_el is not None else ""
        m = WARD_NO.search(name)
        if not m:
            raise ValueError(
                f"placemark {name!r} carries no ward number. Every ward must "
                f"join to locations.ward_no; guessing one would silently "
                f"mis-shade a ward."
            )
        ward_no = int(m.group(1))
        if ward_no in seen:
            raise ValueError(f"ward {ward_no} appears twice in {source.name}")
        seen.add(ward_no)

        data = {}
        for d in pm.iter(f"{KML_NS}Data"):
            key = d.get("name", "").strip()
            value_el = d.find(f"{KML_NS}value")
            if key and value_el is not None:
                data[key] = (value_el.text or "").strip()

        polys = _polygons(pm)
        if not polys:
            raise ValueError(f"ward {ward_no} has no polygon geometry")

        geometry = (
            {"type": "Polygon", "coordinates": polys[0]}
            if len(polys) == 1
            else {"type": "MultiPolygon", "coordinates": polys}
        )
        features.append({
            "type": "Feature",
            # ward_no is a string here to match locations.ward_no, which is
            # VARCHAR — a numeric key would not join without a cast on one side.
            "id": str(ward_no),
            "properties": {
                "ward_no": str(ward_no),
                "ward_name": data.get("Ward Name") or name,
                "zone": data.get("Zone") or None,
            },
            "geometry": geometry,
        })

    if len(features) != N_WARDS:
        raise ValueError(
            f"expected {N_WARDS} wards, parsed {len(features)}. A choropleth "
            f"missing a ward reads as 'nothing happened here', so this is a "
            f"failure rather than a warning."
        )
    features.sort(key=lambda f: int(f["properties"]["ward_no"]))
    return {"type": "FeatureCollection", "features": features}


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    out = pathlib.Path(argv[0]) if argv else DEFAULT_OUT
    fc = build()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(fc, separators=(",", ":")), encoding="utf-8")
    points = sum(
        len(r)
        for f in fc["features"]
        for poly in ([f["geometry"]["coordinates"]]
                     if f["geometry"]["type"] == "Polygon"
                     else f["geometry"]["coordinates"])
        for r in poly
    )
    print(f"{len(fc['features'])} wards, {points:,} points, "
          f"{out.stat().st_size / 1024:.0f} KB -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
