from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GeomLevel


class LocationBase(BaseModel):
    area_name: str = Field(min_length=1, max_length=200)
    ward_no: Optional[str] = Field(default=None, max_length=20)
    ward_name: Optional[str] = Field(default=None, max_length=150)
    zone: Optional[str] = Field(default=None, max_length=100)
    latitude: Optional[Decimal] = Field(default=None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(default=None, ge=-180, le=180)
    geom_level: GeomLevel = GeomLevel.WARD
    is_known_hotspot: bool = False
    hotspot_source: Optional[str] = Field(default=None, max_length=120)
    first_listed_year: Optional[int] = Field(default=None, ge=1900, le=2100)
    elevation_m: Optional[Decimal] = None
    population: Optional[int] = Field(default=None, ge=0)


class LocationCreate(LocationBase):
    city_id: int


class LocationUpdate(BaseModel):
    area_name: Optional[str] = Field(default=None, max_length=200)
    ward_name: Optional[str] = Field(default=None, max_length=150)
    zone: Optional[str] = Field(default=None, max_length=100)
    latitude: Optional[Decimal] = Field(default=None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(default=None, ge=-180, le=180)
    is_known_hotspot: Optional[bool] = None
    last_listed_year: Optional[int] = Field(default=None, ge=1900, le=2100)


class LocationOut(LocationBase):
    model_config = ConfigDict(from_attributes=True)

    location_id: int
    city_id: int
    cell_id: Optional[int] = None
