"""Derived tables: the four things the dashboard reads.

Nothing here is ingested. Every row is computed from `complaints`,
`ward_period_totals`, `weather_daily` and the raw work-order extract, and
every one is reconciled against a committed reference CSV by
`tests/test_derived.py`. Four computations the paper already published are
being reimplemented against a database instead of a dataframe, and the failure
mode that matters is the dashboard quietly disagreeing with the paper.

Read `ufms_schema.sql` section 7 for the full reasoning behind each table;
the column comments below are the short form.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Index, Numeric, String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import PeriodType, WeatherModel
from app.models.types import UInt, USmallInt, UTinyInt

# The detector was measured to find wards that stay above the city norm, not
# wards that are accelerating (profile §25.1: flagged wards end at mean level
# 1.77 vs 1.16, p = 0.0001, but do not exceed their own first-half level,
# p = 0.23). The label is a column value rather than a UI string so the
# distinction cannot be lost between the database and the screen.
CHRONICALLY_ABOVE_NORM = "chronically_above_norm"


class WardQuarterIndex(Base):
    """The relative flooding index per ward-quarter — the project's core quantity.

        rel(w,q) = [events(w,q) + s] / [complaints(w,q) * city_share(q) + s]

    `city_share` sits beside every row so `rel_index` is recomputable from this
    table alone. Both are stored at full precision: rounding the share to eight
    decimal places moves `rel` by roughly 5e-7, which breaks the exact
    reconciliation against the published panel.
    """
    __tablename__ = "ward_quarter_index"
    __table_args__ = (Index("idx_wqi_period", "period_type", "period_start"),)

    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_wqi_location"), primary_key=True)
    period_type: Mapped[PeriodType] = mapped_column(Enum(PeriodType, values_callable=lambda e: [m.value for m in e]), primary_key=True, server_default="quarter")
    period_start: Mapped[date] = mapped_column(Date, primary_key=True, comment="first day of the period")
    event_days: Mapped[int] = mapped_column(UInt, nullable=False, comment="distinct ward-days carrying a strict waterlogging event")
    total_complaints: Mapped[int] = mapped_column(UInt, nullable=False, comment="the denominator, from ward_period_totals: all categories")
    city_share: Mapped[Decimal] = mapped_column(Numeric(20, 18), nullable=False, comment="citywide event-days over citywide complaints, this period")
    smoothing: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, server_default="0.50", comment="added to numerator and denominator; 0.5 in the published panel")
    rel_index: Mapped[Decimal] = mapped_column(Numeric(20, 16), nullable=False, comment="1.00 is the city norm for that quarter")
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class WatchlistSnapshot(Base):
    """A static top-k list frozen at `as_of_date`, with its measured context.

    The three metrics are columns because the screen must show all three
    together: 14.08% precision@20 reads as failure on its own and as 37% of
    achievable against a 4.79% random floor and a 37.72% oracle ceiling.

    They are nullable. A snapshot frozen at today's date has no held-out window
    to score against, and a blank is better than an invented number.
    """
    __tablename__ = "watchlist_snapshots"
    __table_args__ = (
        UniqueConstraint("city_id", "failure_type_id", "as_of_date", "k", name="uq_watchlist_snapshot"),
        Index("idx_wls_as_of", "city_id", "as_of_date"),
    )

    snapshot_id: Mapped[int] = mapped_column(UInt, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(USmallInt, ForeignKey("cities.city_id", ondelete="CASCADE", name="fk_wls_city"), nullable=False)
    failure_type_id: Mapped[int] = mapped_column(UTinyInt, ForeignKey("failure_types.failure_type_id", ondelete="CASCADE", name="fk_wls_type"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False, comment="freeze date: entries rank on events up to and including this day")
    k: Mapped[int] = mapped_column(USmallInt, nullable=False, server_default="20", comment="crew capacity, and the k in precision@k")
    train_start: Mapped[date] = mapped_column(Date, nullable=False)
    test_start: Mapped[Optional[date]] = mapped_column(Date, comment="NULL when the snapshot has not been scored")
    test_end: Mapped[Optional[date]] = mapped_column(Date)
    test_rain_days: Mapped[Optional[int]] = mapped_column(USmallInt, comment="held-out days at or above rain_threshold_mm")
    test_events: Mapped[Optional[int]] = mapped_column(UInt, comment="citywide event-days on those rain days")
    rain_threshold_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), comment="city-mean daily rainfall that defines a rain day")
    weather_model: Mapped[Optional[WeatherModel]] = mapped_column(Enum(WeatherModel, values_callable=lambda e: [m.value for m in e]), comment="which reanalysis defined a rain day")
    precision_at_k: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 8), comment="what the frozen list achieved")
    oracle_at_k: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 8), comment="the ceiling: most nights carry fewer than k events citywide")
    random_at_k: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 8), comment="expected precision of k wards drawn at random")
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "location_id", name="uq_watchlist_entry"),
        Index("idx_wle_location", "location_id"),
    )

    snapshot_id: Mapped[int] = mapped_column(UInt, ForeignKey("watchlist_snapshots.snapshot_id", ondelete="CASCADE", name="fk_wle_snapshot"), primary_key=True)
    rank_position: Mapped[int] = mapped_column(USmallInt, primary_key=True, comment="1 is worst; ties broken by area name so the order is stable")
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_wle_location"), nullable=False)
    prior_events: Mapped[int] = mapped_column(UInt, nullable=False, comment="event-days up to as_of_date. The entire ranking key.")
    test_events: Mapped[Optional[int]] = mapped_column(UInt, comment="event-days on the held-out rain days, for the per-ward column")


class EmergingWatch(Base):
    """Wards ranked by first-half Theil-Sen slope on `rel_index`.

    Benchmarked to the city trend, never to zero: the citywide share fell 22%
    over the window, so testing against zero scored diverging-upward wards as
    declining and produced a false negative (profile §23.1).

    `label` is `chronically_above_norm`, not `accelerating`. That is what the
    detector was measured to find.
    """
    __tablename__ = "emerging_watch"
    __table_args__ = (Index("idx_ew_rank", "as_of_date", "rank_position"),)

    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_ew_location"), primary_key=True)
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True, comment="last day of the detection window")
    window_start: Mapped[date] = mapped_column(Date, nullable=False)
    rank_position: Mapped[int] = mapped_column(USmallInt, nullable=False, comment="by first-half slope, which is the flag rule")
    event_days: Mapped[int] = mapped_column(UInt, nullable=False, comment="over the whole window; eligibility is >= 15")
    half1_slope: Mapped[Decimal] = mapped_column(Numeric(20, 16), nullable=False, comment="Theil-Sen on rel_index per quarter, first half")
    half1_p: Mapped[Decimal] = mapped_column(Numeric(19, 18), nullable=False, comment="Mann-Kendall on the same series")
    half1_level: Mapped[Decimal] = mapped_column(Numeric(20, 16), nullable=False, comment="mean rel_index over the first half")
    half2_level: Mapped[Decimal] = mapped_column(Numeric(20, 16), nullable=False)
    half2_slope: Mapped[Decimal] = mapped_column(Numeric(20, 16), nullable=False)
    level_delta: Mapped[Decimal] = mapped_column(Numeric(21, 16), nullable=False, comment="half2_level minus half1_level")
    full_slope: Mapped[Decimal] = mapped_column(Numeric(20, 16), nullable=False, comment="Theil-Sen over the whole window")
    full_p: Mapped[Decimal] = mapped_column(Numeric(19, 18), nullable=False)
    is_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0", comment="inside the top-N cut this run used")
    on_register: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0", comment="already on the BBMP flood register")
    label: Mapped[str] = mapped_column(String(40), nullable=False, server_default=CHRONICALLY_ABOVE_NORM, comment="what the detector was measured to find, not what it was hoped to find")
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class WardAllocation(Base):
    """Drainage spend per ward beside the change in relative index.

    This is the ALLOCATION screen. The dose-response is retracted (profile
    §27.2) and analysis is closed (§28): `delta_index` is stored because the
    screen plots it, not because spend explains it, and no endpoint returns it
    as an effect.
    """
    __tablename__ = "ward_allocation"
    __table_args__ = (Index("idx_wa_spend", "drainage_spend"),)

    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_wa_location"), primary_key=True)
    window_start: Mapped[date] = mapped_column(Date, primary_key=True, comment="first work completion date counted")
    window_end: Mapped[date] = mapped_column(Date, primary_key=True)
    drainage_works: Mapped[int] = mapped_column(USmallInt, nullable=False, comment="work orders classified as drainage completing in the window")
    drainage_spend: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, comment="INR, nett of deductions")
    ward_area_sqkm: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), comment="what spend actually tracks")
    event_days_pre: Mapped[int] = mapped_column(UInt, nullable=False)
    event_days_post: Mapped[int] = mapped_column(UInt, nullable=False)
    event_days_total: Mapped[int] = mapped_column(UInt, nullable=False, comment="over the whole index window: the absolute-volume axis of the targeting check")
    pre_index: Mapped[Decimal] = mapped_column(Numeric(20, 16), nullable=False, comment="mean rel_index over the pre quarters")
    post_index: Mapped[Decimal] = mapped_column(Numeric(20, 16), nullable=False)
    delta_index: Mapped[Decimal] = mapped_column(Numeric(21, 16), nullable=False, comment="post minus pre. Descriptive. NOT an effect of spend.")
    is_treated: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="any drainage work in the window. 103 of 110; not a usable control split.")
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
