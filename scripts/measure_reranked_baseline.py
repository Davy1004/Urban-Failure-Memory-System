"""Measure the daily re-ranked baseline, on both rainfall bases.

    python scripts/measure_reranked_baseline.py

Why this exists
---------------
`docs/01-evaluation-rules.md` quotes "same list re-ranked daily on all prior
history = 13.70%" as evidence that count-based memory is saturated. That figure
is an **ERA5-basis** number (138 held-out rain days), and it was sitting in a
table whose other rows are **IFS** (136 days). Mixing bases puts a number on a
scale it was not measured against, which is the exact error the evaluation rules
forbid, so the claim was restated as an ERA5 pair (13.55% -> 13.70%) and the
IFS-basis equivalent was left unmeasured. This measures it.

What "re-ranked" means, precisely
---------------------------------
The static list is frozen once, from `WATCHLIST_TRAIN_START..WATCHLIST_AS_OF`.
The re-ranked variant instead rebuilds the ranking **before every test night**,
from every strict event day in `WATCHLIST_TRAIN_START..(night - 1 day)` — so it
is given all the history the static list has *plus* everything that happened
during the test period up to the previous day.

`< night`, strictly, is the whole point: the same day's events are the label, so
including them would be leakage of exactly the kind engineering rule 1 exists to
prevent. Nothing here reads a date on or after the night being scored.

Method validation
-----------------
The re-rank is measured on the ERA5 basis too, not because that number is wanted
but because it is already known: if this script reproduces the published
13.55% -> 13.70% pair, the IFS number it reports on the same code path can be
trusted. If it does not reproduce it, the discrepancy is reported rather than
hidden, and the IFS figure should not be published until it is understood.

Everything is scored by `score_watchlist` from `app/derived/watchlist.py` — the
same function that produces the 14.08% the API serves — so the comparison is
like-for-like by construction rather than by assertion.
"""
from __future__ import annotations

import pathlib
import sys
from datetime import timedelta

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.derived import (  # noqa: E402
    RAIN_THRESHOLD_MM, WATCHLIST_AS_OF, WATCHLIST_K, WATCHLIST_TEST_END,
    WATCHLIST_TEST_START, WATCHLIST_TRAIN_START,
)
from app.derived.watchlist import (  # noqa: E402
    _event_days, _ward_count, rain_days, score_watchlist,
)
from app.ingestion.base import resolve_city  # noqa: E402
from sqlalchemy import text  # noqa: E402

K = WATCHLIST_K


def _names(db, city_id: int) -> dict[int, str]:
    return dict(db.execute(
        text("SELECT location_id, area_name FROM locations WHERE city_id = :c"),
        {"c": city_id},
    ).all())


def _rank(counts: pd.Series, names: dict[int, str], k: int) -> list[int]:
    """Top k by event count, ties broken by area name so runs are reproducible.

    The same tie-break as `build_watchlist`: Bilekahalli and Jakkur both sit on
    64 prior events at the 2023 freeze, and without a deterministic tie-break the
    two methods could differ for a reason that is not about method.
    """
    df = counts.rename("n").reset_index()
    df["area_name"] = df["location_id"].map(names)
    df = df.sort_values(["n", "area_name"], ascending=[False, True])
    return df.head(k)["location_id"].tolist()


def measure(db, city_id: int, model: str, names: dict[int, str], n_wards: int) -> dict:
    days = rain_days(db, city_id, WATCHLIST_TEST_START, WATCHLIST_TEST_END,
                     RAIN_THRESHOLD_MM, model)
    if not days:
        raise SystemExit(f"no rain days on the {model} basis - is weather_daily loaded?")

    # --- the static list, as the API builds it ------------------------------
    train = _event_days(db, city_id, WATCHLIST_TRAIN_START, WATCHLIST_AS_OF)
    frozen = _rank(train.groupby("location_id").size(), names, K)

    test_ev = _event_days(db, city_id, WATCHLIST_TEST_START, WATCHLIST_TEST_END)
    test_ev = test_ev[test_ev["d"].isin(set(days))]
    static = score_watchlist(frozen, test_ev, days, n_wards, K)

    # --- the re-ranked variant ---------------------------------------------
    # All event days from the train start to the last test night, so each night's
    # ranking can be built from strictly-earlier rows without another query.
    hist = _event_days(db, city_id, WATCHLIST_TRAIN_START, WATCHLIST_TEST_END)
    by_night = test_ev.groupby("d")["location_id"].apply(set) if not test_ev.empty \
        else pd.Series(dtype=object)

    hits, sizes, churn = [], [], []
    previous: set[int] | None = None
    for night in days:
        cutoff = night - timedelta(days=1)
        prior = hist[hist["d"] <= cutoff]          # strictly before the night
        top = set(_rank(prior.groupby("location_id").size(), names, K))
        tonight = by_night.get(night, set())
        hits.append(len(tonight & top))
        sizes.append(len(tonight))
        if previous is not None:
            churn.append(K - len(top & previous))
        previous = top

    n = len(days)
    reranked = sum(hits) / n / K

    return {
        "model": model,
        "days": n,
        "events": sum(sizes),
        "static": static["precision_at_k"],
        "reranked": reranked,
        "oracle": static["oracle_at_k"],
        "random": static["random_at_k"],
        "mean_churn": (sum(churn) / len(churn)) if churn else 0.0,
        "frozen_head": [names[i] for i in frozen[:5]],
        "final_head": [names[i] for i in sorted(top)][:0] or
                      [names[i] for i in _rank(
                          hist[hist["d"] <= days[-1] - timedelta(days=1)]
                          .groupby("location_id").size(), names, K)[:5]],
    }


def main() -> int:
    db = SessionLocal()
    try:
        city = resolve_city(db, "Bengaluru")
        names = _names(db, city.city_id)
        n_wards = _ward_count(db, city.city_id)

        print(f"{n_wards} wards, k = {K}, "
              f"train {WATCHLIST_TRAIN_START}..{WATCHLIST_AS_OF}, "
              f"test {WATCHLIST_TEST_START}..{WATCHLIST_TEST_END}\n")

        results = [measure(db, city.city_id, m, names, n_wards)
                   for m in ("era5", "ecmwf_ifs")]
    finally:
        db.close()

    hdr = f"{'basis':<12}{'days':>6}{'events':>8}{'static':>10}{'re-ranked':>11}{'delta':>9}{'oracle':>9}{'random':>9}"
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        print(f"{r['model']:<12}{r['days']:>6}{r['events']:>8}"
              f"{r['static'] * 100:>9.2f}%{r['reranked'] * 100:>10.2f}%"
              f"{(r['reranked'] - r['static']) * 100:>+8.2f}%"
              f"{r['oracle'] * 100:>8.2f}%{r['random'] * 100:>8.2f}%")

    print()
    for r in results:
        print(f"{r['model']}: mean overlap churn between consecutive nights' "
              f"top-{K} = {r['mean_churn']:.2f} of {K}")
        print(f"  frozen head: {', '.join(r['frozen_head'])}")

    era5 = next(r for r in results if r["model"] == "era5")
    print("\nMethod validation against the published ERA5 pair "
          "(13.55% static -> 13.70% re-ranked):")
    for label, got, want in (("static", era5["static"] * 100, 13.55),
                             ("re-ranked", era5["reranked"] * 100, 13.70)):
        mark = "reproduced" if abs(got - want) < 0.06 else "DOES NOT MATCH"
        print(f"  {label:<10} published {want:.2f}%  measured {got:.2f}%   {mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
