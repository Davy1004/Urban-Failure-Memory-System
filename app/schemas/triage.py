"""The nightly priority list — the product's primary output."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import RiskLevel


class TriageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank_position: int
    location_id: int
    area_name: str
    ward_no: Optional[str] = None
    score: Decimal
    risk_level: Optional[RiskLevel] = None
    # Why this location is on the list tonight — the officer-facing reason.
    reason: Optional[str] = None
    recurrence_percentile: Optional[Decimal] = None
    rain_sensitivity_mm: Optional[Decimal] = None
    forecast_rain_mm: Optional[Decimal] = None
    in_top_k: bool = False


class TriageList(BaseModel):
    city_id: int
    city_name: str
    ranking_date: date
    failure_type: str
    model_name: Optional[str] = None
    k: int
    items: List[TriageItem]


class EmergingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    location_id: int
    area_name: str
    ward_no: Optional[str] = None
    trend_statistic: Optional[Decimal] = None
    p_value: Optional[Decimal] = None
    months_of_evidence: Optional[int] = None
    status: str
