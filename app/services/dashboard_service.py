"""The four screens, assembled.

This layer's real job is not query orchestration — the repository does that.
It is making sure a number never leaves the API without the context that stops
it being misread. Three specific things it refuses to do:

* return a watchlist without its ceiling and floor;
* describe an emerging ward as *accelerating*, or imply a flag can be validated
  against the city's own register additions (it cannot: `first_listed_year` is
  NULL for all 398 register points);
* return any coefficient on drainage spend.

The caveat strings are here rather than in the frontend on purpose. A frontend
can drop a paragraph in a redesign; a required response field cannot.
"""
from datetime import date
from typing import List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.derived import EMERGING_MIN_EVENTS
from app.derived.allocation import allocation_summary
from app.derived.emerging import level_persistence
from app.models.derived import CHRONICALLY_ABOVE_NORM
from app.repositories.dashboard_repo import DashboardRepository
from app.schemas.dashboard import (
    AllocationFinding, AllocationItem, AllocationOut, CityIndexSnapshot,
    CityIndexWard, Correlation, EmergingEvidence, EmergingItem, EmergingOut,
    IndexPoint, IndexSeries, WatchlistContext, WatchlistItem, WatchlistOut,
)

DEFAULT_CITY = "Bengaluru"

EMERGING_CAVEATS = [
    "The label is 'chronically above norm', not 'accelerating'. Wards in the "
    "top 10 by first-half slope end the second half at mean relative index "
    "1.77 against 1.16 for all eligible wards (p = 0.0001) and 10 of 10 finish "
    "above the city norm - but they do not significantly exceed their own "
    "first-half level (p = 0.23). The detector finds wards that stay bad.",
    "The ranking is a rank cut, not a significance test. Benjamini-Hochberg "
    "over all 103 eligible wards leaves zero survivors at q = 0.05, 0.10 or "
    "0.20, and exactly one - Jakkur - under the pre-specified off-register "
    "pool. 'More wards rise than chance allows' is defensible (permutation "
    "p = 0.0010); 'these nine wards are rising' is not.",
    "Trends are benchmarked to the city, never to zero. The citywide share of "
    "flooding complaints fell 22% over the window, so a ward whose share fell "
    "5% was diverging upward. Against a zero null the same data gives 0 rising "
    "and 10 declining; against the city trend, 9 and 4.",
    "There is no ground truth for a flag. The register KMLs carry no year, so "
    "locations.first_listed_year is NULL for all 398 points and 'which "
    "locations did the city add this year' cannot be checked.",
    "A share decline is not improvement without checking absolute counts. Four "
    "of the ten wards that decline against a zero null had absolute events "
    "rise; that is denominator growth, not recovery.",
]

ALLOCATION_HEADLINE = (
    "BBMP allocates drainage spend by ward size, not by flooding need. Spend "
    "correlates with ward area at Spearman +0.474 and with the ward's relative "
    "flooding index at +0.082 (p = 0.39). It correlates with absolute complaint "
    "counts at +0.274 only because large wards generate more complaints of "
    "every kind - controlling for area that collapses to -0.050 (p = 0.60). "
    "Only 20% of works sit under per-ward budget heads, so allocation is "
    "discretionary and still untargeted."
)

ALLOCATION_RETRACTION = (
    "This screen shows allocation, not outcome. The published dose-response of "
    "the change in relative index on log drainage spend (-0.0240, p = 0.0138, "
    "n = 110) is RETRACTED: refitted on treated wards only it is -0.0064 "
    "(p = 0.833), because log1p(spend) placed 7 untreated wards at 0 against "
    "every treated ward at 16-20 and the slope was fitted through two clusters. "
    "Those 7 are not a valid control - 5 had Rs 37-121 M of drainage work "
    "before the window. And no other design is available: drainage works are "
    "distributed continuously and near-uniformly across all 198 wards and have "
    "been since 2013, so no observational evaluation of their effect is "
    "identifiable from these records - the treatment does not vary enough for "
    "any design to exploit."
)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DashboardRepository(db)

    def _city(self, city_name: str):
        city = self.repo.city_by_name(city_name)
        if city is None:
            raise NotFoundError(f"City {city_name!r} is not loaded.")
        return city

    # -- /index/{ward} ---------------------------------------------------
    def index_series(self, ward: str, city_name: str = DEFAULT_CITY) -> IndexSeries:
        city = self._city(city_name)
        loc = self.repo.ward(city.city_id, ward)
        if loc is None:
            raise NotFoundError(
                f"No ward {ward!r} in {city.name}. Use the exact area name or "
                f"the BBMP ward number; ward names are not fuzzy-matched."
            )
        rows = self.repo.index_series(loc.location_id)
        if not rows:
            raise NotFoundError(
                f"No relative index for {loc.area_name}. Run "
                f"`python -m app.ingestion.cli derive` to build it."
            )
        points = [
            IndexPoint(
                period=str(pd.Timestamp(r.period_start).to_period("Q")),
                period_start=r.period_start,
                event_days=r.event_days,
                total_complaints=r.total_complaints,
                city_share=float(r.city_share),
                expected_event_days=float(r.total_complaints) * float(r.city_share),
                rel_index=float(r.rel_index),
            )
            for r in rows
        ]
        return IndexSeries(
            location_id=loc.location_id,
            ward=loc.area_name,
            ward_no=loc.ward_no,
            zone=loc.zone,
            smoothing=float(rows[0].smoothing),
            mean_rel_index=sum(p.rel_index for p in points) / len(points),
            quarters=len(points),
            points=points,
        )

    def city_index(self, city_name: str = DEFAULT_CITY,
                   period: Optional[str] = None) -> CityIndexSnapshot:
        """Every ward's index for one quarter — the choropleth's data.

        `period` is a quarter label such as "2024Q3"; omitted, it is the most
        recent quarter the index covers.
        """
        city = self._city(city_name)
        periods = self.repo.index_periods(city.city_id)
        if not periods:
            raise NotFoundError(
                f"No relative index for {city.name}. Run "
                f"`python -m app.ingestion.cli derive` to build it."
            )
        labels = [str(pd.Timestamp(p).to_period("Q")) for p in periods]

        if period is None:
            chosen, chosen_label = periods[-1], labels[-1]
        else:
            wanted = period.strip().upper()
            if wanted not in labels:
                raise NotFoundError(
                    f"{period!r} is not a quarter the index covers. "
                    f"Available: {labels[0]}..{labels[-1]}."
                )
            chosen, chosen_label = periods[labels.index(wanted)], wanted

        rows = self.repo.index_snapshot(city.city_id, chosen)
        if not rows:
            raise NotFoundError(f"No index rows for {chosen_label}.")

        return CityIndexSnapshot(
            city=city.name,
            period=chosen_label,
            period_start=chosen,
            # One share per quarter by construction; the reconciliation test
            # asserts that, so reading it off the first row is safe.
            city_share=float(rows[0][0].city_share),
            available_periods=labels,
            wards=[
                CityIndexWard(
                    location_id=q.location_id,
                    ward=loc.area_name,
                    ward_no=loc.ward_no,
                    zone=loc.zone,
                    event_days=q.event_days,
                    total_complaints=q.total_complaints,
                    expected_event_days=float(q.total_complaints) * float(q.city_share),
                    rel_index=float(q.rel_index),
                )
                for q, loc in rows
            ],
        )

    # -- /watchlist ------------------------------------------------------
    def watchlist(self, city_name: str = DEFAULT_CITY,
                  failure_code: str = "WATERLOG",
                  as_of: Optional[date] = None,
                  k: Optional[int] = None) -> WatchlistOut:
        city = self._city(city_name)
        snap = self.repo.latest_snapshot(city.city_id, failure_code,
                                         as_of.isoformat() if as_of else None, k)
        if snap is None:
            raise NotFoundError(
                f"No {failure_code} watchlist snapshot for {city.name}"
                + (f" as of {as_of}" if as_of else "")
                + ". Run `python -m app.ingestion.cli derive`."
            )
        rows = self.repo.watchlist_entries(snap.snapshot_id)
        precision = float(snap.precision_at_k) if snap.precision_at_k is not None else None
        oracle = float(snap.oracle_at_k) if snap.oracle_at_k is not None else None

        return WatchlistOut(
            snapshot_id=snap.snapshot_id,
            city=city.name,
            failure_type=failure_code,
            as_of_date=snap.as_of_date,
            k=snap.k,
            train_start=snap.train_start,
            computed_at=snap.computed_at,
            context=WatchlistContext(
                precision_at_k=precision,
                oracle_at_k=oracle,
                random_at_k=float(snap.random_at_k) if snap.random_at_k is not None else None,
                share_of_ceiling=(precision / oracle
                                  if precision is not None and oracle else None),
                test_rain_days=snap.test_rain_days,
                test_events=snap.test_events,
                test_start=snap.test_start,
                test_end=snap.test_end,
                rain_threshold_mm=(float(snap.rain_threshold_mm)
                                   if snap.rain_threshold_mm is not None else None),
                weather_model=(snap.weather_model.value
                               if snap.weather_model is not None else None),
            ),
            items=[
                WatchlistItem(
                    rank_position=e.rank_position,
                    location_id=e.location_id,
                    ward=loc.area_name,
                    ward_no=loc.ward_no,
                    zone=loc.zone,
                    prior_events=e.prior_events,
                    test_events=e.test_events,
                )
                for e, loc in rows
            ],
        )

    # -- /emerging -------------------------------------------------------
    def emerging(self, city_name: str = DEFAULT_CITY,
                 flagged_only: bool = False,
                 off_register_only: bool = False,
                 limit: Optional[int] = None) -> EmergingOut:
        city = self._city(city_name)
        rows = self.repo.emerging(city.city_id, flagged_only, off_register_only,
                                  limit)
        if not rows:
            raise NotFoundError(
                f"No emerging watch for {city.name}. Run "
                f"`python -m app.ingestion.cli derive`."
            )
        all_rows = self.repo.emerging(city.city_id)
        first = all_rows[0][0]
        evidence = level_persistence(self.db, city.city_id)

        return EmergingOut(
            city=city.name,
            as_of_date=first.as_of_date,
            window_start=first.window_start,
            eligible_wards=len(all_rows),
            min_event_days=EMERGING_MIN_EVENTS,
            flagged=sum(1 for w, _ in all_rows if w.is_flagged),
            label=CHRONICALLY_ABOVE_NORM,
            ground_truth_available=False,
            evidence=EmergingEvidence(**evidence),
            caveats=EMERGING_CAVEATS,
            items=[
                EmergingItem(
                    rank_position=w.rank_position,
                    location_id=w.location_id,
                    ward=loc.area_name,
                    ward_no=loc.ward_no,
                    zone=loc.zone,
                    is_flagged=bool(w.is_flagged),
                    on_register=bool(w.on_register),
                    event_days=w.event_days,
                    half1_slope=float(w.half1_slope),
                    half1_p=float(w.half1_p),
                    half1_level=float(w.half1_level),
                    half2_level=float(w.half2_level),
                    level_delta=float(w.level_delta),
                    full_slope=float(w.full_slope),
                    full_p=float(w.full_p),
                )
                for w, loc in rows
            ],
        )

    # -- /allocation -----------------------------------------------------
    def allocation(self, city_name: str = DEFAULT_CITY,
                   treated_only: bool = False) -> AllocationOut:
        city = self._city(city_name)
        rows = self.repo.allocation(city.city_id, treated_only)
        if not rows:
            raise NotFoundError(
                f"No allocation panel for {city.name}. Run "
                f"`python -m app.ingestion.cli derive`."
            )
        summary = allocation_summary(self.db, city.city_id)
        first = rows[0][0]

        items: List[AllocationItem] = []
        for a, loc in rows:
            area = float(a.ward_area_sqkm) if a.ward_area_sqkm is not None else None
            spend = float(a.drainage_spend)
            items.append(AllocationItem(
                location_id=a.location_id,
                ward=loc.area_name,
                ward_no=loc.ward_no,
                zone=loc.zone,
                is_treated=bool(a.is_treated),
                drainage_works=a.drainage_works,
                drainage_spend=spend,
                ward_area_sqkm=area,
                spend_per_sqkm=(spend / area) if area else None,
                event_days_total=a.event_days_total,
                pre_index=float(a.pre_index),
                post_index=float(a.post_index),
                delta_index=float(a.delta_index),
            ))

        return AllocationOut(
            city=city.name,
            window_start=first.window_start,
            window_end=first.window_end,
            finding=AllocationFinding(
                n_wards=summary["n_wards"],
                n_treated=summary["n_treated"],
                n_untreated=summary["n_untreated"],
                total_spend=summary["total_spend"],
                median_spend_treated=summary["median_spend_treated"],
                spend_vs_area=Correlation(**summary["spend_vs_area"]),
                spend_vs_pre_index=Correlation(**summary["spend_vs_pre_index"]),
                spend_vs_absolute_events=Correlation(**summary["spend_vs_absolute_events"]),
                area_vs_absolute_events=Correlation(**summary["area_vs_absolute_events"]),
                spend_vs_events_controlling_area=Correlation(
                    **summary["spend_vs_events_controlling_area"]),
            ),
            headline=ALLOCATION_HEADLINE,
            retraction=ALLOCATION_RETRACTION,
            items=items,
        )
