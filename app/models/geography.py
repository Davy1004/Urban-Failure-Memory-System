"""Cities, weather grid cells, locations, assets, and data provenance."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    AssetStatus, AssetType, CityRole, FailureScope, GeomLevel, IngestionStatus,
)
from app.models.types import UBigInt, UInt, USmallInt, UTinyInt


class City(Base):
    __tablename__ = "cities"
    __table_args__ = (UniqueConstraint("name", "state", name="uq_cities_name"),)

    city_id: Mapped[int] = mapped_column(USmallInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="IN")
    centroid_lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    centroid_lng: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    timezone: Mapped[str] = mapped_column(String(40), nullable=False, default="Asia/Kolkata")
    role: Mapped[CityRole] = mapped_column(Enum(CityRole, values_callable=lambda e: [m.value for m in e]), nullable=False)
    monsoon_start_month: Mapped[int] = mapped_column(UTinyInt, nullable=False)
    monsoon_end_month: Mapped[int] = mapped_column(UTinyInt, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    locations: Mapped[List["Location"]] = relationship(back_populates="city", cascade="all, delete-orphan")
    weather_cells: Mapped[List["WeatherCell"]] = relationship(back_populates="city", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<City {self.name} ({self.role})>"


class WeatherCell(Base):
    """One ERA5 reanalysis grid point (~25 km). A city needs only a handful,
    which is what keeps hourly weather inside a 1 GB free tier."""
    __tablename__ = "weather_cells"
    __table_args__ = (UniqueConstraint("latitude", "longitude", name="uq_cell_coords"),)

    cell_id: Mapped[int] = mapped_column(UInt, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(USmallInt, ForeignKey("cities.city_id", ondelete="CASCADE"), nullable=False, index=True)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    elevation_m: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 2))

    city: Mapped["City"] = relationship(back_populates="weather_cells")


class DataSource(Base):
    __tablename__ = "data_sources"

    source_id: Mapped[int] = mapped_column(USmallInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    url: Mapped[Optional[str]] = mapped_column(String(500))
    licence: Mapped[Optional[str]] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(String(500))


class IngestionRun(Base):
    """Provenance. Every ingested row points back to one of these."""
    __tablename__ = "ingestion_runs"
    __table_args__ = (Index("idx_run_source_time", "source_id", "started_at"),)

    run_id: Mapped[int] = mapped_column(UBigInt, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(USmallInt, ForeignKey("data_sources.source_id", ondelete="RESTRICT"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rows_ingested: Mapped[int] = mapped_column(UInt, nullable=False, default=0)
    rows_rejected: Mapped[int] = mapped_column(UInt, nullable=False, default=0)
    status: Mapped[IngestionStatus] = mapped_column(Enum(IngestionStatus, values_callable=lambda e: [m.value for m in e]), nullable=False, default=IngestionStatus.RUNNING)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    source: Mapped["DataSource"] = relationship()


class FailureType(Base):
    __tablename__ = "failure_types"

    failure_type_id: Mapped[int] = mapped_column(UTinyInt, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(400))
    scope: Mapped[FailureScope] = mapped_column(Enum(FailureScope, values_callable=lambda e: [m.value for m in e]), nullable=False, default=FailureScope.SCHEMA_ONLY)


class Location(Base):
    """A ward (Bengaluru) or a named hotspot (Delhi). The analysis unit."""
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("city_id", "area_name", "geom_level", name="uq_location_city_area"),
        Index("idx_location_ward", "city_id", "ward_no"),
        Index("idx_location_hotspot", "city_id", "is_known_hotspot"),
        Index("idx_location_coords", "latitude", "longitude"),
    )

    location_id: Mapped[int] = mapped_column(UInt, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(USmallInt, ForeignKey("cities.city_id", ondelete="CASCADE"), nullable=False, index=True)
    cell_id: Mapped[Optional[int]] = mapped_column(UInt, ForeignKey("weather_cells.cell_id", ondelete="SET NULL"), index=True)
    area_name: Mapped[str] = mapped_column(String(200), nullable=False)
    ward_no: Mapped[Optional[str]] = mapped_column(String(20))
    ward_name: Mapped[Optional[str]] = mapped_column(String(150))
    zone: Mapped[Optional[str]] = mapped_column(String(100))
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6))
    geom_level: Mapped[GeomLevel] = mapped_column(Enum(GeomLevel, values_callable=lambda e: [m.value for m in e]), nullable=False, default=GeomLevel.WARD)

    # On the municipality's own published hotspot register?
    is_known_hotspot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hotspot_source: Mapped[Optional[str]] = mapped_column(String(120))
    first_listed_year: Mapped[Optional[int]] = mapped_column(USmallInt)
    last_listed_year: Mapped[Optional[int]] = mapped_column(USmallInt)

    elevation_m: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 2))
    imperviousness: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    drain_distance_m: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 2))
    population: Mapped[Optional[int]] = mapped_column(UInt)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    city: Mapped["City"] = relationship(back_populates="locations")
    cell: Mapped[Optional["WeatherCell"]] = relationship()
    assets: Mapped[List["InfrastructureAsset"]] = relationship(back_populates="location", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Location {self.area_name} ward={self.ward_no}>"


class InfrastructureAsset(Base):
    __tablename__ = "infrastructure_assets"

    asset_id: Mapped[int] = mapped_column(UInt, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType, values_callable=lambda e: [m.value for m in e]), nullable=False)
    installation_date: Mapped[Optional[date]] = mapped_column()
    capacity_note: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus, values_callable=lambda e: [m.value for m in e]), nullable=False, default=AssetStatus.UNKNOWN)

    location: Mapped["Location"] = relationship(back_populates="assets")
