from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.location import LocationCreate, LocationOut, LocationUpdate
from app.services.location_service import LocationService

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=Page[LocationOut])
def list_locations(
    city_id: Optional[int] = None,
    q: Optional[str] = Query(default=None, description="substring match on area name"),
    hotspots_only: bool = Query(default=False, description="only the municipality's published register"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[LocationOut]:
    svc = LocationService(db)
    rows = svc.search(city_id, q, hotspots_only, limit, offset)
    return Page[LocationOut](
        items=[LocationOut.model_validate(r) for r in rows],
        total=svc.count(city_id),
        limit=limit,
        offset=offset,
    )


@router.get("/{location_id}", response_model=LocationOut)
def get_location(
    location_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> LocationOut:
    return LocationOut.model_validate(LocationService(db).get(location_id))


@router.post("", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> LocationOut:
    return LocationOut.model_validate(LocationService(db).create(payload))


@router.patch("/{location_id}", response_model=LocationOut)
def update_location(
    location_id: int,
    payload: LocationUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> LocationOut:
    return LocationOut.model_validate(LocationService(db).update(location_id, payload))


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    LocationService(db).delete(location_id)
