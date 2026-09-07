from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.geography import Location
from app.repositories.base import BaseRepository


class LocationRepository(BaseRepository[Location]):
    def __init__(self, db: Session):
        super().__init__(Location, db)

    def search(
        self,
        city_id: Optional[int] = None,
        q: Optional[str] = None,
        hotspots_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Location]:
        stmt = select(Location)
        if city_id is not None:
            stmt = stmt.where(Location.city_id == city_id)
        if hotspots_only:
            stmt = stmt.where(Location.is_known_hotspot.is_(True))
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(Location.area_name.like(like))
        stmt = stmt.order_by(Location.area_name).limit(limit).offset(offset)
        return self.db.execute(stmt).scalars().all()

    def hotspot_register(self, city_id: int) -> Sequence[Location]:
        """The municipality's own published list — the triage candidate set."""
        stmt = (
            select(Location)
            .where(Location.city_id == city_id, Location.is_known_hotspot.is_(True))
            .order_by(Location.area_name)
        )
        return self.db.execute(stmt).scalars().all()
