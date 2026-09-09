"""Derived tables: the four computations the dashboard screens read.

Ingestion loads facts; this package computes the quantities the paper reports.
The split matters because these four are reimplementations — every number here
was first produced by a CSV-based analysis script, and the committed reference
CSVs under `data/reference/` are the record of what those scripts produced.
`tests/test_derived.py` reconciles each table against them exactly.

Build order matters: `ward_quarter_index` is the base, and `emerging_watch`
and `ward_allocation` are both computed from it rather than from `complaints`
a second time. `build_all` runs them in order.

Every window below is the one the published analysis used. They are module
constants rather than call-site literals so that a rebuild cannot silently
drift from the paper.
"""
from datetime import date

# The index panel: 20 complete quarters, 2020Q2 through 2025Q1. The complaint
# extract runs 2020-02-08 to 2025-06-19, so 2020Q1 and 2025Q2 are partial and
# are excluded (profile §25.2).
INDEX_START = date(2020, 4, 1)
INDEX_END = date(2025, 4, 1)          # exclusive

# The +0.5 in numerator and denominator of the relative index (profile §23.1).
SMOOTHING = 0.5

# Watchlist: freeze the ranking on everything up to the end of 2023, score it
# on the rain days of 2024-01-01..2025-06-19 (profile §14.2, §17.3 variant B).
WATCHLIST_TRAIN_START = date(2020, 2, 8)
WATCHLIST_AS_OF = date(2023, 12, 31)
WATCHLIST_TEST_START = date(2024, 1, 1)
WATCHLIST_TEST_END = date(2025, 6, 19)
WATCHLIST_K = 20
RAIN_THRESHOLD_MM = 2.5
RAIN_MODEL = "ecmwf_ifs"

# Emerging: eligibility and the split point of the two halves (profile §25.1).
EMERGING_MIN_EVENTS = 15
EMERGING_FLAG_TOP_N = 10

# Allocation: works completing in this window, against pre 2020Q2-2020Q4 and
# post 2023Q1-2025Q1, on the 110 wards with >= 8 strict events (profile §25.2).
WORKS_WINDOW_START = date(2021, 1, 1)
WORKS_WINDOW_END = date(2022, 12, 31)
ALLOCATION_PRE_END = date(2021, 1, 1)   # exclusive: pre is everything before
ALLOCATION_POST_YEAR = 2023             # post is 2023Q1 onward
ALLOCATION_MIN_EVENTS = 8

__all__ = [
    "INDEX_START", "INDEX_END", "SMOOTHING",
    "WATCHLIST_TRAIN_START", "WATCHLIST_AS_OF", "WATCHLIST_TEST_START",
    "WATCHLIST_TEST_END", "WATCHLIST_K", "RAIN_THRESHOLD_MM", "RAIN_MODEL",
    "EMERGING_MIN_EVENTS", "EMERGING_FLAG_TOP_N",
    "WORKS_WINDOW_START", "WORKS_WINDOW_END", "ALLOCATION_PRE_END",
    "ALLOCATION_POST_YEAR", "ALLOCATION_MIN_EVENTS",
    "build_all",
]


def build_all(db, city_name: str = "Bengaluru", raw_dir=None) -> dict:
    """Rebuild all four derived tables in dependency order."""
    import pathlib

    from app.derived.allocation import build_allocation
    from app.derived.emerging import build_emerging
    from app.derived.index import build_index
    from app.derived.watchlist import build_watchlist

    raw = pathlib.Path(raw_dir) if raw_dir else pathlib.Path("data/raw")
    return {
        "ward_quarter_index": build_index(db, city_name),
        "watchlist": build_watchlist(db, city_name),
        "emerging_watch": build_emerging(db, city_name),
        "ward_allocation": build_allocation(db, raw, city_name),
    }
