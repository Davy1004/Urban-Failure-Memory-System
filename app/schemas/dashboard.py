"""Response models for the four dashboard screens.

Several fields here exist to stop a screen being read as more than it is, and
they are not optional decoration:

* `WatchlistOut` carries `oracle_at_k` and `random_at_k` beside
  `precision_at_k`, because 14% alone reads as failure and 14% against a 4.8%
  floor and a 37.7% ceiling reads as 37% of achievable.
* `EmergingOut.label` is `chronically_above_norm`, and `caveats` says in words
  what the detector was measured to do. There is no external ground truth to
  confirm a flag against — `locations.first_listed_year` is NULL for all 398
  register points — and `EmergingOut.ground_truth_available` says so.
* `AllocationOut` returns correlations and no coefficient. The dose-response is
  retracted (profile §27.2) and no outcome design is identifiable on this data
  (§28), so there is nothing to put in a `coefficient` field and the field does
  not exist.
"""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Correlation(BaseModel):
    """A correlation with its p-value. Never one without the other."""
    rho: float
    p: float


# --------------------------------------------------------------------------
# /index/{ward}
# --------------------------------------------------------------------------

INDEX_DEFINITION = (
    "rel = (event_days + s) / (total_complaints * city_share + s). "
    "Above 1.00 the ward had more flooding event-days than the citywide "
    "complaint mix predicts for its volume; below 1.00, fewer. Normalising "
    "by the ward's own complaint volume is mandatory - raw counts rise "
    "because reporting doubled 2021-2024, not because flooding did."
)


class IndexPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: str = Field(examples=["2023Q2"])
    period_start: date
    event_days: int = Field(description="distinct days with a strict waterlogging event")
    total_complaints: int = Field(description="the ward's complaints across every category")
    city_share: float = Field(description="citywide event-days over complaints, this quarter")
    expected_event_days: float = Field(description="total_complaints * city_share")
    rel_index: float = Field(description="1.00 is the city norm for the quarter")


class IndexSeries(BaseModel):
    location_id: int
    ward: str
    ward_no: Optional[str] = None
    zone: Optional[str] = None
    smoothing: float
    mean_rel_index: float
    quarters: int
    points: List[IndexPoint]
    definition: str = INDEX_DEFINITION


class CityIndexWard(BaseModel):
    """One ward's index for a single quarter — a row of the choropleth."""
    model_config = ConfigDict(from_attributes=True)

    location_id: int
    ward: str
    ward_no: Optional[str] = None
    zone: Optional[str] = None
    event_days: int
    total_complaints: int
    expected_event_days: float
    rel_index: float


class CityIndexSnapshot(BaseModel):
    """Every ward for one quarter.

    The map needs all 198 wards at once. Assembling it from 198 per-ward
    requests would let a single failure render a half-shaded choropleth, and a
    ward missing its colour reads as "nothing happened here" rather than "no
    data" — a different and worse claim.
    """
    city: str
    period: str = Field(examples=["2025Q1"])
    period_start: date
    city_share: float = Field(
        description="citywide event-days over complaints for this quarter")
    available_periods: List[str]
    wards: List[CityIndexWard]
    definition: str = INDEX_DEFINITION


# --------------------------------------------------------------------------
# /watchlist
# --------------------------------------------------------------------------

class WatchlistItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank_position: int
    location_id: int
    ward: str
    ward_no: Optional[str] = None
    zone: Optional[str] = None
    prior_events: int = Field(description="event-days up to the freeze date; the ranking key")
    test_events: Optional[int] = Field(
        default=None, description="event-days on the held-out rain days")


class WatchlistContext(BaseModel):
    """The three figures that have to travel with the list."""
    precision_at_k: Optional[float] = Field(
        default=None, description="what the frozen list achieved on held-out rain days")
    oracle_at_k: Optional[float] = Field(
        default=None, description="the ceiling: most nights carry fewer than k events citywide")
    random_at_k: Optional[float] = Field(
        default=None, description="expected precision of k wards drawn at random")
    share_of_ceiling: Optional[float] = Field(
        default=None, description="precision_at_k / oracle_at_k")
    test_rain_days: Optional[int] = None
    test_events: Optional[int] = None
    test_start: Optional[date] = None
    test_end: Optional[date] = None
    rain_threshold_mm: Optional[float] = None
    weather_model: Optional[str] = None
    reading: str = (
        "Report all three together, always. A precision@20 of 14% reads as "
        "failure alone; against a 4.8% random floor and a 37.7% oracle ceiling "
        "it is 37% of everything achievable. The ceiling is below 50% because a "
        "median rain night carries about 6 strict events citywide, so 20 crew "
        "slots cannot all be right."
    )


class WatchlistOut(BaseModel):
    snapshot_id: int
    city: str
    failure_type: str
    as_of_date: date
    k: int
    train_start: date
    computed_at: datetime
    context: WatchlistContext
    items: List[WatchlistItem]


# --------------------------------------------------------------------------
# /emerging
# --------------------------------------------------------------------------

class EmergingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank_position: int
    location_id: int
    ward: str
    ward_no: Optional[str] = None
    zone: Optional[str] = None
    is_flagged: bool
    on_register: bool = Field(description="already on BBMP's own flood register")
    event_days: int
    half1_slope: float = Field(description="Theil-Sen on rel_index, first half; the flag rule")
    half1_p: float = Field(description="Mann-Kendall on the same series")
    half1_level: float
    half2_level: float
    level_delta: float
    full_slope: float = Field(description="Theil-Sen over the whole window")
    full_p: float


class EmergingEvidence(BaseModel):
    """What the detector was measured to do — not what a rising slope suggests."""
    flagged_n: int
    flagged_half1_level: float
    flagged_half2_level: float
    all_half2_level: float
    flagged_above_norm: int = Field(description="of flagged_n, how many ended above the city norm")
    p_vs_other_wards: float
    p_vs_own_first_half: float


class EmergingOut(BaseModel):
    city: str
    as_of_date: date
    window_start: date
    eligible_wards: int
    min_event_days: int
    flagged: int
    label: str = Field(examples=["chronically_above_norm"])
    ground_truth_available: bool = Field(
        default=False,
        description="whether flags can be validated against the city's own additions")
    evidence: EmergingEvidence
    items: List[EmergingItem]
    caveats: List[str]


# --------------------------------------------------------------------------
# /allocation
# --------------------------------------------------------------------------

class AllocationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location_id: int
    ward: str
    ward_no: Optional[str] = None
    zone: Optional[str] = None
    is_treated: bool
    drainage_works: int
    drainage_spend: float = Field(description="INR, nett of deductions")
    ward_area_sqkm: Optional[float] = None
    spend_per_sqkm: Optional[float] = None
    event_days_total: int
    pre_index: float
    post_index: float
    delta_index: float = Field(
        description="post minus pre. Descriptive only - NOT an effect of spend.")


class AllocationFinding(BaseModel):
    n_wards: int
    n_treated: int
    n_untreated: int
    total_spend: float
    median_spend_treated: float
    spend_vs_area: Correlation
    spend_vs_pre_index: Correlation
    spend_vs_absolute_events: Correlation
    area_vs_absolute_events: Correlation
    spend_vs_events_controlling_area: Correlation


class AllocationOut(BaseModel):
    city: str
    window_start: date
    window_end: date
    finding: AllocationFinding
    headline: str
    retraction: str
    items: List[AllocationItem]
