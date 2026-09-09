"""Reads for the four derived tables. No SQLAlchemy above this layer."""
from datetime import date
from typing import Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.derived import (
    EmergingWatch, WardAllocation, WardQuarterIndex, WatchlistEntry,
    WatchlistSnapshot,
)
from app.models.enums import GeomLevel, PeriodType
from app.models.geography import City, FailureType, Location


class DashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    # -- shared ----------------------------------------------------------
    def city_by_name(self, name: str) -> Optional[City]:
        return self.db.execute(
            select(City).where(City.name.ilike(name.strip()))
        ).scalar_one_or_none()

    def ward(self, city_id: int, ward: str) -> Optional[Location]:
        """Resolve a ward by `area_name` or by `ward_no`.

        A URL carrying a ward name is friendlier for a demo; a ward number is
        what an officer has. Both work, exact match only — fuzzy-matching ward
        names is what the crosswalk exists to stop anyone doing ad hoc.
        """
        stmt = select(Location).where(
            Location.city_id == city_id,
            Location.geom_level == GeomLevel.WARD,
        )
        by_name = self.db.execute(
            stmt.where(Location.area_name == ward)
        ).scalar_one_or_none()
        if by_name is not None:
            return by_name
        return self.db.execute(
            stmt.where(Location.ward_no == str(ward).strip())
        ).scalar_one_or_none()

    # -- index -----------------------------------------------------------
    def index_series(self, location_id: int) -> Sequence[WardQuarterIndex]:
        return self.db.execute(
            select(WardQuarterIndex)
            .where(WardQuarterIndex.location_id == location_id,
                   WardQuarterIndex.period_type == PeriodType.QUARTER)
            .order_by(WardQuarterIndex.period_start)
        ).scalars().all()

    def index_periods(self, city_id: int) -> Sequence[date]:
        return self.db.execute(
            select(WardQuarterIndex.period_start)
            .join(Location, Location.location_id == WardQuarterIndex.location_id)
            .where(Location.city_id == city_id,
                   WardQuarterIndex.period_type == PeriodType.QUARTER)
            .distinct()
            .order_by(WardQuarterIndex.period_start)
        ).scalars().all()

    def index_snapshot(self, city_id: int, period_start: date
                       ) -> Sequence[Tuple[WardQuarterIndex, Location]]:
        """Every ward's index for one quarter — what the choropleth shades.

        A per-ward endpoint would mean 198 requests to draw one map, and a map
        assembled from 198 responses can render half-shaded when one fails.
        """
        return self.db.execute(
            select(WardQuarterIndex, Location)
            .join(Location, Location.location_id == WardQuarterIndex.location_id)
            .where(Location.city_id == city_id,
                   WardQuarterIndex.period_type == PeriodType.QUARTER,
                   WardQuarterIndex.period_start == period_start)
            .order_by(Location.area_name)
        ).all()

    # -- watchlist -------------------------------------------------------
    def latest_snapshot(self, city_id: int, failure_code: str,
                        as_of: Optional[str] = None,
                        k: Optional[int] = None) -> Optional[WatchlistSnapshot]:
        stmt = (
            select(WatchlistSnapshot)
            .join(FailureType,
                  FailureType.failure_type_id == WatchlistSnapshot.failure_type_id)
            .where(WatchlistSnapshot.city_id == city_id,
                   FailureType.code == failure_code)
            .order_by(WatchlistSnapshot.as_of_date.desc(),
                      WatchlistSnapshot.snapshot_id.desc())
        )
        if as_of is not None:
            stmt = stmt.where(WatchlistSnapshot.as_of_date == as_of)
        if k is not None:
            stmt = stmt.where(WatchlistSnapshot.k == k)
        return self.db.execute(stmt.limit(1)).scalars().first()

    def watchlist_entries(self, snapshot_id: int
                          ) -> Sequence[Tuple[WatchlistEntry, Location]]:
        return self.db.execute(
            select(WatchlistEntry, Location)
            .join(Location, Location.location_id == WatchlistEntry.location_id)
            .where(WatchlistEntry.snapshot_id == snapshot_id)
            .order_by(WatchlistEntry.rank_position)
        ).all()

    # -- emerging --------------------------------------------------------
    def emerging(self, city_id: int, flagged_only: bool = False,
                 off_register_only: bool = False, limit: Optional[int] = None
                 ) -> Sequence[Tuple[EmergingWatch, Location]]:
        stmt = (
            select(EmergingWatch, Location)
            .join(Location, Location.location_id == EmergingWatch.location_id)
            .where(Location.city_id == city_id)
            .order_by(EmergingWatch.rank_position)
        )
        if flagged_only:
            stmt = stmt.where(EmergingWatch.is_flagged.is_(True))
        if off_register_only:
            stmt = stmt.where(EmergingWatch.on_register.is_(False))
        if limit is not None:
            stmt = stmt.limit(limit)
        return self.db.execute(stmt).all()

    # -- allocation ------------------------------------------------------
    def allocation(self, city_id: int, treated_only: bool = False
                   ) -> Sequence[Tuple[WardAllocation, Location]]:
        stmt = (
            select(WardAllocation, Location)
            .join(Location, Location.location_id == WardAllocation.location_id)
            .where(Location.city_id == city_id)
            .order_by(WardAllocation.drainage_spend.desc())
        )
        if treated_only:
            stmt = stmt.where(WardAllocation.is_treated.is_(True))
        return self.db.execute(stmt).all()
