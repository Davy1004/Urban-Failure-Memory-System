"""Raw signal: weather, complaints, and the failure events derived from them."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Date, DateTime, Enum, ForeignKey, Index, Numeric, SmallInteger, String,
    Text, TIMESTAMP, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    CollectionStatus, ComplaintStatus, CongestionLevel, DerivedFrom, PeriodType,
    Severity,
)
from app.models.types import UBigInt, UInt, USmallInt, UTinyInt


class WeatherObservation(Base):
    """Hourly ERA5, one row per cell per hour.

    The unique constraint is not cosmetic: without it a retried scheduler
    run double-inserts silently and skews every downstream aggregate.
    """
    __tablename__ = "weather_observations"
    __table_args__ = (
        UniqueConstraint("cell_id", "recorded_at", name="uq_weather_cell_time"),
        Index("idx_weather_time", "recorded_at"),
    )

    weather_id: Mapped[int] = mapped_column(UBigInt, primary_key=True, autoincrement=True)
    cell_id: Mapped[int] = mapped_column(UInt, ForeignKey("weather_cells.cell_id", ondelete="CASCADE", name="fk_weather_cell"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    rainfall_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 3))
    temperature_c: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    humidity_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    wind_speed_ms: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    source_id: Mapped[Optional[int]] = mapped_column(USmallInt, ForeignKey("data_sources.source_id", ondelete="SET NULL", name="fk_weather_source"))


class WeatherDaily(Base):
    """Derived daily features. Intensity beats totals: 60 mm in an hour
    floods a road, 60 mm over a day usually does not."""
    __tablename__ = "weather_daily"
    __table_args__ = (Index("idx_wd_date", "obs_date"),)

    cell_id: Mapped[int] = mapped_column(UInt, ForeignKey("weather_cells.cell_id", ondelete="CASCADE", name="fk_wd_cell"), primary_key=True)
    obs_date: Mapped[date] = mapped_column(Date, primary_key=True)
    rain_24h_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 2))
    rain_1h_max_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 2))
    rain_3h_max_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 2))
    antecedent_7d_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), comment="prior-week total, a soil saturation proxy")
    # Normalised, city-invariant. A 1-in-10-year event means the same
    # thing everywhere; "60 mm" does not.
    rain_percentile: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 5), comment="rank of rain_24h in this cell own history")
    return_period_yrs: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3))
    season_position: Mapped[Optional[int]] = mapped_column(SmallInteger, comment="days into the LOCAL monsoon, not calendar month")
    temp_mean_c: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    humidity_mean_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))


class Complaint(Base):
    """A citizen complaint — the raw signal, NOT a confirmed failure.

    Reporting propensity varies with income and civic awareness, so any
    analysis must control for each location's baseline complaint rate.
    """
    __tablename__ = "complaints"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_complaint_external"),
        Index("idx_complaint_loc_time", "location_id", "reported_at"),
        Index("idx_complaint_type_time", "failure_type_id", "reported_at"),
    )

    complaint_id: Mapped[int] = mapped_column(UBigInt, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_complaint_location"), nullable=False)
    failure_type_id: Mapped[Optional[int]] = mapped_column(UTinyInt, ForeignKey("failure_types.failure_type_id", ondelete="SET NULL", name="fk_complaint_type"))
    external_id: Mapped[Optional[str]] = mapped_column(String(80), comment="id in the source system, for dedup")
    reported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    category: Mapped[Optional[str]] = mapped_column(String(150), comment="raw category string from source")
    sub_category: Mapped[Optional[str]] = mapped_column(String(150))
    status: Mapped[ComplaintStatus] = mapped_column(Enum(ComplaintStatus, values_callable=lambda e: [m.value for m in e]), nullable=False, default=ComplaintStatus.UNKNOWN, server_default="unknown")
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_id: Mapped[Optional[int]] = mapped_column(USmallInt, ForeignKey("data_sources.source_id", ondelete="SET NULL", name="fk_complaint_source"))
    run_id: Mapped[Optional[int]] = mapped_column(UBigInt, ForeignKey("ingestion_runs.run_id", ondelete="SET NULL", name="fk_complaint_run"))

    location: Mapped["Location"] = relationship()


class Failure(Base):
    """A confirmed failure event, usually derived by clustering complaints
    in space and time. occurred_at and reported_at are separate because the
    lag between them is both a feature and a source of bias."""
    __tablename__ = "failures"
    __table_args__ = (
        Index("idx_failure_loc_time", "location_id", "occurred_at"),
        Index("idx_failure_type_time", "failure_type_id", "occurred_at"),
        Index("idx_failure_occurred", "occurred_at"),
    )

    failure_id: Mapped[int] = mapped_column(UBigInt, primary_key=True, autoincrement=True)
    failure_type_id: Mapped[int] = mapped_column(UTinyInt, ForeignKey("failure_types.failure_type_id", ondelete="RESTRICT", name="fk_failure_type"), nullable=False)
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_failure_location"), nullable=False)
    asset_id: Mapped[Optional[int]] = mapped_column(UInt, ForeignKey("infrastructure_assets.asset_id", ondelete="SET NULL", name="fk_failure_asset"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reported_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    severity_level: Mapped[Severity] = mapped_column(Enum(Severity, values_callable=lambda e: [m.value for m in e]), nullable=False, default=Severity.MEDIUM, server_default="medium")
    description: Mapped[Optional[str]] = mapped_column(Text)
    derived_from: Mapped[DerivedFrom] = mapped_column(Enum(DerivedFrom, values_callable=lambda e: [m.value for m in e]), nullable=False, default=DerivedFrom.MANUAL, server_default="manual")
    complaint_count: Mapped[Optional[int]] = mapped_column(USmallInt, comment="size of the cluster, if derived")
    source_id: Mapped[Optional[int]] = mapped_column(USmallInt, ForeignKey("data_sources.source_id", ondelete="SET NULL", name="fk_failure_source"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)

    location: Mapped["Location"] = relationship()
    failure_type: Mapped["FailureType"] = relationship()


class ComplaintFailureLink(Base):
    __tablename__ = "complaint_failure_link"
    __table_args__ = (
        Index("idx_cfl_failure", "failure_id"),
    )

    complaint_id: Mapped[int] = mapped_column(UBigInt, ForeignKey("complaints.complaint_id", ondelete="CASCADE", name="fk_cfl_complaint"), primary_key=True)
    failure_id: Mapped[int] = mapped_column(UBigInt, ForeignKey("failures.failure_id", ondelete="CASCADE", name="fk_cfl_failure"), primary_key=True)


class WardPeriodTotal(Base):
    """The denominator of the relative flooding index.

    `complaints` holds only the hazard subset rule 7 allows to be loaded, so a
    ward's total complaint volume across every category is not recoverable from
    it. This table carries it, so the index can be rebuilt from the database
    alone rather than from a CSV beside it.
    """
    __tablename__ = "ward_period_totals"
    __table_args__ = (Index("idx_wpt_period", "period_type", "period_start"),)

    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_wpt_location"), primary_key=True)
    period_type: Mapped[PeriodType] = mapped_column(Enum(PeriodType, values_callable=lambda e: [m.value for m in e]), primary_key=True, server_default="quarter")
    period_start: Mapped[date] = mapped_column(Date, primary_key=True, comment="first day of the period")
    total_complaints: Mapped[int] = mapped_column(UInt, nullable=False, comment="all categories, not just hazards")
    run_id: Mapped[Optional[int]] = mapped_column(UBigInt, ForeignKey("ingestion_runs.run_id", ondelete="SET NULL", name="fk_wpt_run"))


class SanitationData(Base):
    __tablename__ = "sanitation_data"
    __table_args__ = (UniqueConstraint("location_id", "recorded_at", name="uq_sanitation_loc_time"),)

    sanitation_id: Mapped[int] = mapped_column(UBigInt, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_sanitation_location"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    garbage_volume_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    collection_status: Mapped[CollectionStatus] = mapped_column(Enum(CollectionStatus, values_callable=lambda e: [m.value for m in e]), nullable=False, default=CollectionStatus.UNKNOWN, server_default="unknown")
    source_id: Mapped[Optional[int]] = mapped_column(USmallInt)


class TrafficData(Base):
    """Schema-only in rev 2 — retained for extensibility, no module built."""
    __tablename__ = "traffic_data"
    __table_args__ = (UniqueConstraint("location_id", "recorded_at", name="uq_traffic_loc_time"),)

    traffic_id: Mapped[int] = mapped_column(UBigInt, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_traffic_location"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    vehicle_count: Mapped[Optional[int]] = mapped_column(UInt)
    congestion_level: Mapped[Optional[CongestionLevel]] = mapped_column(Enum(CongestionLevel, values_callable=lambda e: [m.value for m in e]))
    average_speed_kmph: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    source_id: Mapped[Optional[int]] = mapped_column(USmallInt)
