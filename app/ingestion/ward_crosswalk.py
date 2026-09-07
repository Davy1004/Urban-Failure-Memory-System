"""Ward crosswalk: complaint ward NAME -> BBMP ward NUMBER.

The grievance CSVs carry ward names only; the flood-prone register carries
ward numbers plus coordinates. The two spellings disagree, so
`data/reference/ward_crosswalk.csv` is a hand-checked artifact, not something
recomputed at import time. See docs/02-data-profile.md §15.

Never fuzzy-match here. If a name is not in the CSV the loader must fail
loudly rather than invent a ward: a silently mis-assigned ward corrupts every
downstream memory value, and nothing later in the pipeline would catch it.

Two different reasons a row can lack a ward number, and they are NOT the same:

  not_in_register  the register lists flood-vulnerable locations in only 103
                   of 198 wards. The other 96 are perfectly valid wards whose
                   number this source cannot supply. They STAY in the panel.
  unresolved       we could not decide which ward this name refers to. These
                   are excluded, and the excluded count and row share are
                   logged on every run.

Collapsing those two would drop ~40% of complaint rows from the panel while
looking like routine data cleaning, which is exactly the failure this file
exists to prevent.
"""
from __future__ import annotations

import csv
import logging
import pathlib
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set

logger = logging.getLogger("ufms.ingestion.crosswalk")

CROSSWALK_PATH = (
    pathlib.Path(__file__).resolve().parents[2] / "data" / "reference" / "ward_crosswalk.csv"
)

VALID_METHODS = {"exact", "normalised", "manual", "not_in_register", "unresolved"}

# Only this method is excluded from the panel.
EXCLUDED_METHODS = {"unresolved"}


@dataclass(frozen=True)
class WardMapping:
    complaint_ward_name: str
    register_ward_no: Optional[int]
    register_ward_name: Optional[str]
    match_method: str
    notes: str

    @property
    def is_excluded(self) -> bool:
        return self.match_method in EXCLUDED_METHODS

    @property
    def has_ward_no(self) -> bool:
        return self.register_ward_no is not None


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
            if r.match_method in {"exact", "normalised", "manual"} and not r.has_ward_no:
                raise ValueError(
                    f"{r.complaint_ward_name!r} is marked {r.match_method} but has no "
                    f"register_ward_no"
                )
            if r.match_method in {"not_in_register", "unresolved"} and r.has_ward_no:
                raise ValueError(
                    f"{r.complaint_ward_name!r} is marked {r.match_method} but carries "
                    f"a register_ward_no"
                )
            if r.match_method in {"manual", "unresolved"} and not r.notes.strip():
                raise ValueError(
                    f"{r.complaint_ward_name!r} is {r.match_method} and must carry a note"
                )
            self._by_name[r.complaint_ward_name] = r

        seen: Dict[int, str] = {}
        for r in self._by_name.values():
            if r.has_ward_no:
                if r.register_ward_no in seen:
                    raise ValueError(
                        f"register ward {r.register_ward_no} claimed by both "
                        f"{seen[r.register_ward_no]!r} and {r.complaint_ward_name!r}"
                    )
                seen[r.register_ward_no] = r.complaint_ward_name

    def __len__(self) -> int:
        return len(self._by_name)

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def get(self, name: str) -> WardMapping:
        try:
            return self._by_name[name]
        except KeyError:
            raise KeyError(
                f"ward name {name!r} is not in the crosswalk. Add it to "
                f"data/reference/ward_crosswalk.csv by hand — do not fuzzy-match."
            ) from None

    def ward_no(self, name: str) -> Optional[int]:
        return self.get(name).register_ward_no

    @property
    def excluded_names(self) -> Set[str]:
        return {n for n, r in self._by_name.items() if r.is_excluded}

    def counts_by_method(self) -> Dict[str, int]:
        out: Dict[str, int] = {m: 0 for m in VALID_METHODS}
        for r in self._by_name.values():
            out[r.match_method] += 1
        return out


def load_crosswalk(path: pathlib.Path = CROSSWALK_PATH) -> WardCrosswalk:
    if not path.exists():
        raise FileNotFoundError(
            f"ward crosswalk not found at {path}. It is a committed, hand-checked "
            f"artifact; it is not generated at runtime."
        )
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        for d in csv.DictReader(fh):
            no = (d.get("register_ward_no") or "").strip()
            rows.append(WardMapping(
                complaint_ward_name=d["complaint_ward_name"],
                register_ward_no=int(no) if no else None,
                register_ward_name=(d.get("register_ward_name") or "").strip() or None,
                match_method=(d.get("match_method") or "").strip(),
                notes=(d.get("notes") or "").strip(),
            ))
    return WardCrosswalk(rows)


def apply_to_ward_series(ward_names, crosswalk: Optional[WardCrosswalk] = None):
    """Split a pandas Series of complaint ward names into kept and excluded.

    Returns (keep_mask, report). Logs the excluded row count and share on
    every call — a shrinking panel that nobody notices is the failure mode
    this reporting exists to prevent, so it is unconditional, not debug-level.
    """
    import pandas as pd  # local import: keeps the module importable without pandas

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
            "ward crosswalk: 0 rows excluded of %s; %d ward names mapped to a ward "
            "number, %d valid wards absent from the register (kept)",
            f"{total:,}",
            report["wards_by_method"]["exact"] + report["wards_by_method"]["normalised"]
            + report["wards_by_method"]["manual"],
            report["wards_by_method"]["not_in_register"],
        )
    if n_null:
        logger.info("%s row(s) had a null ward name and were dropped", f"{n_null:,}")
    return keep, report
