"""Ward crosswalk: complaint ward NAME -> BBMP ward NUMBER, centroid and zone.

The grievance CSVs carry ward names only. `data/reference/ward_crosswalk.csv`
is a hand-checked artifact mapping each of the 198 complaint ward names onto
the BBMP 198-ward delimitation, with the polygon centroid for each.
See docs/02-data-profile.md §15 and §16.

The authority is `bbmp_ward_map_2015.kml`, the 198-ward delimitation in force
for the whole complaint period (2020-02 .. 2025-06). The flood register was
never the right authority for ward numbers: it covers only 103 of 198 wards,
and its points are flood-prone *locations*, so using them as ward positions
would bias every centroid toward low ground.

`in_flood_register` is kept as a column because it is a real feature, not a
matching artifact: it is the ward-level form of `is_known_hotspot`. Triage
ranks the wards on the register; emerging detection scans the ones that are
not. Never filter on it.

Never fuzzy-match here. If a name is not in the CSV the loader fails loudly
rather than inventing a ward — a silently mis-assigned ward corrupts every
downstream memory value and nothing later would catch it.
"""
from __future__ import annotations

import csv
import logging
import math
import pathlib
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger("ufms.ingestion.crosswalk")

CROSSWALK_PATH = (
    pathlib.Path(__file__).resolve().parents[2] / "data" / "reference" / "ward_crosswalk.csv"
)

VALID_METHODS = {"exact", "normalised", "manual", "unresolved"}

# Only this method is excluded from the panel. A ward absent from the flood
# register is NOT excluded — see the module docstring.
EXCLUDED_METHODS = {"unresolved"}

N_BBMP_WARDS = 198


@dataclass(frozen=True)
class WardMapping:
    complaint_ward_name: str
    bbmp_ward_no: Optional[int]
    bbmp_ward_name: Optional[str]
    bbmp_zone: Optional[str]
    centroid_lat: Optional[float]
    centroid_lon: Optional[float]
    ward_area_sqkm: Optional[float]
    match_method: str
    in_flood_register: bool
    register_ward_name: Optional[str]
    notes: str

    @property
    def is_excluded(self) -> bool:
        return self.match_method in EXCLUDED_METHODS

    @property
    def has_ward_no(self) -> bool:
        return self.bbmp_ward_no is not None

    @property
    def has_centroid(self) -> bool:
        return self.centroid_lat is not None and self.centroid_lon is not None


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres. Ample for nearest-cell assignment."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class WardCrosswalk:
    def __init__(self, rows: Iterable[WardMapping]):
        self._by_name: Dict[str, WardMapping] = {}
        for r in rows:
            if r.complaint_ward_name in self._by_name:
                raise ValueError(
                    f"duplicate complaint_ward_name in crosswalk: {r.complaint_ward_name!r}"
                )
            if r.match_method not in VALID_METHODS:
                raise ValueError(
                    f"unknown match_method {r.match_method!r} for "
                    f"{r.complaint_ward_name!r}; expected one of {sorted(VALID_METHODS)}"
                )
            if r.match_method == "unresolved":
                if r.has_ward_no:
                    raise ValueError(
                        f"{r.complaint_ward_name!r} is unresolved but carries a ward number"
                    )
            else:
                if not r.has_ward_no:
                    raise ValueError(
                        f"{r.complaint_ward_name!r} is {r.match_method} but has no "
                        f"bbmp_ward_no"
                    )
                if not (1 <= r.bbmp_ward_no <= N_BBMP_WARDS):
                    raise ValueError(
                        f"{r.complaint_ward_name!r} has ward number {r.bbmp_ward_no} "
                        f"outside 1..{N_BBMP_WARDS}"
                    )
                if not r.has_centroid:
                    raise ValueError(
                        f"{r.complaint_ward_name!r} is {r.match_method} but has no centroid"
                    )
            if r.match_method in {"manual", "unresolved"} and not r.notes.strip():
                raise ValueError(
                    f"{r.complaint_ward_name!r} is {r.match_method} and must carry a note"
                )
            self._by_name[r.complaint_ward_name] = r

        seen: Dict[int, str] = {}
        for r in self._by_name.values():
            if r.has_ward_no:
                if r.bbmp_ward_no in seen:
                    raise ValueError(
                        f"BBMP ward {r.bbmp_ward_no} claimed by both "
                        f"{seen[r.bbmp_ward_no]!r} and {r.complaint_ward_name!r}"
                    )
                seen[r.bbmp_ward_no] = r.complaint_ward_name

    def __len__(self) -> int:
        return len(self._by_name)

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def __iter__(self):
        return iter(self._by_name.values())

    def get(self, name: str) -> WardMapping:
        try:
            return self._by_name[name]
        except KeyError:
            raise KeyError(
                f"ward name {name!r} is not in the crosswalk. Add it to "
                f"data/reference/ward_crosswalk.csv by hand — do not fuzzy-match."
            ) from None

    def ward_no(self, name: str) -> Optional[int]:
        return self.get(name).bbmp_ward_no

    def centroid(self, name: str) -> Optional[Tuple[float, float]]:
        r = self.get(name)
        return (r.centroid_lat, r.centroid_lon) if r.has_centroid else None

    @property
    def excluded_names(self) -> Set[str]:
        return {n for n, r in self._by_name.items() if r.is_excluded}

    @property
    def register_wards(self) -> Set[str]:
        """Wards on BBMP's own flood register — the triage population."""
        return {n for n, r in self._by_name.items() if r.in_flood_register}

    @property
    def non_register_wards(self) -> Set[str]:
        """Wards NOT on the register — the Proof Two emerging-detection pool."""
        return {n for n, r in self._by_name.items() if not r.in_flood_register}

    def counts_by_method(self) -> Dict[str, int]:
        out: Dict[str, int] = {m: 0 for m in VALID_METHODS}
        for r in self._by_name.values():
            out[r.match_method] += 1
        return out

    def nearest_cell(self, name: str,
                     cells: Sequence[Tuple[int, float, float]]) -> Optional[int]:
        """cells is a sequence of (cell_id, lat, lon). Returns the nearest id."""
        c = self.centroid(name)
        if c is None or not cells:
            return None
        lat, lon = c
        return min(cells, key=lambda t: haversine_m(lat, lon, t[1], t[2]))[0]


def _f(v: str) -> Optional[float]:
    v = (v or "").strip()
    return float(v) if v else None


def load_crosswalk(path: pathlib.Path = CROSSWALK_PATH) -> WardCrosswalk:
    if not path.exists():
        raise FileNotFoundError(
            f"ward crosswalk not found at {path}. It is a committed, hand-checked "
            f"artifact; it is not generated at runtime."
        )
    rows: List[WardMapping] = []
    with path.open(newline="", encoding="utf-8") as fh:
        for d in csv.DictReader(fh):
            no = (d.get("bbmp_ward_no") or "").strip()
            rows.append(WardMapping(
                complaint_ward_name=d["complaint_ward_name"],
                bbmp_ward_no=int(no) if no else None,
                bbmp_ward_name=(d.get("bbmp_ward_name") or "").strip() or None,
                bbmp_zone=(d.get("bbmp_zone") or "").strip() or None,
                centroid_lat=_f(d.get("centroid_lat")),
                centroid_lon=_f(d.get("centroid_lon")),
                ward_area_sqkm=_f(d.get("ward_area_sqkm")),
                match_method=(d.get("match_method") or "").strip(),
                in_flood_register=(d.get("in_flood_register") or "").strip().lower() == "true",
                register_ward_name=(d.get("register_ward_name") or "").strip() or None,
                notes=(d.get("notes") or "").strip(),
            ))
    return WardCrosswalk(rows)


def apply_to_ward_series(ward_names, crosswalk: Optional[WardCrosswalk] = None):
    """Split a pandas Series of complaint ward names into kept and excluded.

    Returns (keep_mask, report). Logs the excluded row count and share on
    every call — a shrinking panel that nobody notices is the failure mode
    this reporting exists to prevent, so it is unconditional.
    """
    import pandas as pd  # local: keeps the module importable without pandas

    cw = crosswalk or load_crosswalk()
    s = pd.Series(ward_names)
    known = s.dropna()

    unknown = sorted(set(known) - set(cw._by_name))
    if unknown:
        raise KeyError(
            f"{len(unknown)} ward name(s) absent from the crosswalk: {unknown[:10]}"
            f"{' ...' if len(unknown) > 10 else ''}. Resolve them by hand in "
            f"data/reference/ward_crosswalk.csv."
        )

    excluded = cw.excluded_names
    keep = ~s.isin(excluded) & s.notna()

    total = len(s)
    n_null = int(s.isna().sum())
    n_excl = int(s.isin(excluded).sum())
    report = {
        "rows_total": total,
        "rows_kept": int(keep.sum()),
        "rows_excluded_unresolved": n_excl,
        "rows_null_ward": n_null,
        "excluded_share_pct": (100.0 * n_excl / total) if total else 0.0,
        "excluded_ward_names": sorted(excluded),
        "wards_by_method": cw.counts_by_method(),
    }

    if n_excl:
        logger.warning(
            "ward crosswalk excluded %s of %s rows (%.2f%%) across %d unresolved "
            "ward name(s): %s",
            f"{n_excl:,}", f"{total:,}", report["excluded_share_pct"],
            len(excluded), sorted(excluded),
        )
    else:
        logger.info(
            "ward crosswalk: 0 rows excluded of %s; all %d ward names carry a BBMP "
            "ward number (%d on the flood register, %d not)",
            f"{total:,}", len(cw), len(cw.register_wards), len(cw.non_register_wards),
        )
    if n_null:
        logger.info("%s row(s) had a null ward name and were dropped", f"{n_null:,}")
    return keep, report
