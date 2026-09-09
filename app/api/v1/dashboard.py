"""The four dashboard endpoints.

    GET /api/v1/index          every ward's index for one quarter (the map)
    GET /api/v1/index/{ward}   the relative flooding index, quarterly
    GET /api/v1/watchlist      the standing top-k, with its measured context
    GET /api/v1/emerging       the rank-based detector
    GET /api/v1/allocation     drainage spend against ward size

All four are read-only and all four are open to both roles. Officers are the
users these screens exist for; nothing here mutates state, so `require_admin`
would only stop the people meant to read it. Writes happen through the derive
CLI, which is deliberately not an endpoint — rebuilding the index takes a pass
over 237,157 complaints and 49,915 work orders, and a dashboard should not be
able to trigger that.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import (
    AllocationOut, CityIndexSnapshot, EmergingOut, IndexSeries, WatchlistOut,
)
from app.services.dashboard_service import DEFAULT_CITY, DashboardService

index_router = APIRouter(prefix="/index", tags=["index"])
watchlist_router = APIRouter(prefix="/watchlist", tags=["watchlist"])
emerging_router = APIRouter(prefix="/emerging", tags=["emerging"])
allocation_router = APIRouter(prefix="/allocation", tags=["allocation"])


@index_router.get("", response_model=CityIndexSnapshot)
def city_index(
    city: str = Query(default=DEFAULT_CITY),
    period: Optional[str] = Query(default=None,
                                  description="quarter label, e.g. 2024Q3; defaults to the latest"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CityIndexSnapshot:
    """Every ward's index for one quarter — what the choropleth shades.

    A collection read rather than 198 calls to the route below: a map built
    from 198 responses renders half-shaded when one of them fails, and a ward
    with no colour reads as "nothing happened here" rather than "no data".
    """
    return DashboardService(db).city_index(city, period)


@index_router.get("/{ward}", response_model=IndexSeries)
def ward_index(
    ward: str = Path(description="exact ward area name, or the BBMP ward number"),
    city: str = Query(default=DEFAULT_CITY),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> IndexSeries:
    """The ward's relative flooding index per quarter, with its inputs.

    Every point carries `event_days`, `total_complaints` and `city_share`, so a
    reader can see the index is a benchmarked ratio rather than a count. Raw
    counts rose because complaint volume doubled 2021-2024, and normalising by
    the ward's own volume is what separates that from flooding.
    """
    return DashboardService(db).index_series(ward, city)


@watchlist_router.get("", response_model=WatchlistOut)
def watchlist(
    city: str = Query(default=DEFAULT_CITY),
    failure_type: str = Query(default="WATERLOG"),
    as_of: Optional[date] = Query(default=None, description="defaults to the latest snapshot"),
    k: Optional[int] = Query(default=None, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> WatchlistOut:
    """The standing top-k list, and the three figures that make it readable.

    `context` carries the achieved precision@k, the oracle ceiling and the
    random floor together. A client showing the list without them is showing
    the officer something they already have, with none of the measurement that
    says how good it is.
    """
    return DashboardService(db).watchlist(city, failure_type, as_of, k)


@emerging_router.get("", response_model=EmergingOut)
def emerging(
    city: str = Query(default=DEFAULT_CITY),
    flagged_only: bool = Query(default=False, description="only the top-N rank cut"),
    off_register: bool = Query(default=False,
                               description="only wards not on BBMP's flood register"),
    limit: Optional[int] = Query(default=None, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> EmergingOut:
    """Wards ranked by first-half trend in the relative index.

    The response carries `label`, `evidence` and `caveats` because the ranking
    on its own would be read as "these wards are accelerating", which is not
    what was measured. `ground_truth_available` is False and stays False until
    the register carries listing years.
    """
    return DashboardService(db).emerging(city, flagged_only, off_register, limit)


@allocation_router.get("", response_model=AllocationOut)
def allocation(
    city: str = Query(default=DEFAULT_CITY),
    treated_only: bool = Query(default=False,
                               description="drop the 7 wards with no work in the window"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> AllocationOut:
    """Drainage spend per ward against ward size and relative flooding need.

    Allocation, not outcome. `finding` returns correlations and no coefficient:
    the dose-response is retracted and no outcome design is identifiable on
    this data. `retraction` says so in the payload so a client cannot present
    `delta_index` as an effect of spend without contradicting the response it
    rendered from.
    """
    return DashboardService(db).allocation(city, treated_only)
