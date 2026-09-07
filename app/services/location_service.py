from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.geography import Location
from app.repositories.location_repo import LocationRepository
from app.schemas.location import LocationCreate, LocationUpdate


class LocationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = LocationRepository(db)

    def get(self, location_id: int) -> Location:
        loc = self.repo.get(location_id)
        if not loc:
            raise NotFoundError(f"Location {location_id} not found.")
        return loc

    def search(self, city_id: Optional[int], q: Optional[str],
               hotspots_only: bool, limit: int, offset: int) -> Sequence[Location]:
        return self.repo.search(city_id, q, hotspots_only, limit, offset)

    def count(self, city_id: Optional[int] = None) -> int:
        return self.repo.count(city_id=city_id)

    def create(self, payload: LocationCreate) -> Location:
        loc = Location(**payload.model_dump())
        self.repo.add(loc)
        self.db.commit()
        self.db.refresh(loc)
        return loc

    def update(self, location_id: int, payload: LocationUpdate) -> Location:
        loc = self.get(location_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(loc, field, value)
        self.db.commit()
        self.db.refresh(loc)
        return loc

    def delete(self, location_id: int) -> None:
        loc = self.get(location_id)
        self.repo.delete(loc)
        self.db.commit()
