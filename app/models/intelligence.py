"""Memory, patterns, models, predictions, rankings, emerging hotspots."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Index, JSON, Numeric,
    String, TIMESTAMP, UniqueConstraint, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    Algorithm, EmergingMethod, EmergingStatus, FeatureSet, PatternOperator,
    PredictionOutcome, RiskLevel,
)
from app.models.types import UBigInt, UInt, USmallInt, UTinyInt


class FailureMemory(Base):
    """The Failure Memory Index, as of a date.

    LEAKAGE RULE: every value in a row must be computed from data strictly
    EARLIER than as_of_date. Break this and every metric downstream is void.
    """
    __tablename__ = "failure_memory"
    __table_args__ = (
        UniqueConstraint("location_id", "failure_type_id", "as_of_date", name="uq_memory"),
        Index("idx_memory_asof", "as_of_date"),
    )

    memory_id: Mapped[int] = mapped_column(UBigInt, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_memory_location"), nullable=False)
    failure_type_id: Mapped[int] = mapped_column(UTinyInt, ForeignKey("failure_types.failure_type_id", ondelete="CASCADE", name="fk_memory_type"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)

    recurrence_count: Mapped[Optional[int]] = mapped_column(USmallInt)
    recurrence_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4), comment="events per season")
    # Rank within the city. This is the form that transfers across cities.
    recurrence_percentile: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 5), comment="rank within city — this is what transfers")
    days_since_last: Mapped[Optional[int]] = mapped_column()
    severity_ema: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    # Rainfall at which THIS location has historically failed. The heart
    # of the system: two sites get the same rain, only history separates them.
    rain_sensitivity_mm: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 2), comment="rainfall at which THIS location has historically failed")
    neighbour_memory: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 4), comment="same stats within 1 km")
    baseline_complaint_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 4), comment="reporting-bias control")

    location: Mapped["Location"] = relationship()


class DetectedPattern(Base):
    """Human-readable rules, stored structured so they can be ranked and served.
    e.g. feature='rain_24h_mm', operator='>', threshold=60, confidence=0.72"""
    __tablename__ = "detected_patterns"
    __table_args__ = (
        Index("idx_pattern_loc_type", "location_id", "failure_type_id"),
        Index("idx_pattern_conf", "confidence"),
    )

    pattern_id: Mapped[int] = mapped_column(UInt, primary_key=True, autoincrement=True)
    location_id: Mapped[Optional[int]] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_pattern_location"), comment="NULL = city-wide rule")
    failure_type_id: Mapped[int] = mapped_column(UTinyInt, ForeignKey("failure_types.failure_type_id", ondelete="CASCADE", name="fk_pattern_type"), nullable=False)
    feature: Mapped[str] = mapped_column(String(80), nullable=False)
    operator: Mapped[PatternOperator] = mapped_column(Enum(PatternOperator, values_callable=lambda e: [m.value for m in e]), nullable=False)
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    threshold_upper: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), comment="used when operator = between")
    season: Mapped[Optional[str]] = mapped_column(String(40))
    support_count: Mapped[int] = mapped_column(UInt, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    lift: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)

    def as_sentence(self) -> str:
        """What an officer actually reads on the dashboard."""
        return (f"{self.feature} {self.operator.value} {self.threshold_value} "
                f"-> failure (confidence {float(self.confidence):.0%}, "
                f"{self.support_count} past events)")


class MLModel(Base):
    """Model registry. Table is `models`; the class is MLModel to avoid
    colliding with the app.models package name."""
    __tablename__ = "models"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_name_version"),
        Index("idx_model_active", "is_active", "city_id"),
    )

    model_id: Mapped[int] = mapped_column(UInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    algorithm: Mapped[Algorithm] = mapped_column(Enum(Algorithm, values_callable=lambda e: [m.value for m in e]), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    city_id: Mapped[Optional[int]] = mapped_column(USmallInt)
    failure_type_id: Mapped[Optional[int]] = mapped_column(UTinyInt)
    feature_set: Mapped[FeatureSet] = mapped_column(Enum(FeatureSet, values_callable=lambda e: [m.value for m in e]), nullable=False)
    train_start: Mapped[Optional[date]] = mapped_column(Date)
    train_end: Mapped[Optional[date]] = mapped_column(Date)
    test_start: Mapped[Optional[date]] = mapped_column(Date)
    test_end: Mapped[Optional[date]] = mapped_column(Date)
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, comment="pr_auc, precision_at_20, brier, ece, base_rate")
    artifact_path: Mapped[Optional[str]] = mapped_column(String(400))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"))
    trained_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class RiskPrediction(Base):
    """One row per (location, hazard, target date, model).

    actual_outcome is what closes the loop. Without it you can never show
    the alerts were right, which is the entire value proposition.
    """
    __tablename__ = "risk_predictions"
    __table_args__ = (
        UniqueConstraint("location_id", "failure_type_id", "predicted_for_date", "model_id", name="uq_prediction"),
        Index("idx_pred_date", "predicted_for_date", "risk_score"),
        Index("idx_pred_outcome", "actual_outcome", "predicted_for_date"),
    )

    prediction_id: Mapped[int] = mapped_column(UBigInt, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_pred_location"), nullable=False)
    failure_type_id: Mapped[int] = mapped_column(UTinyInt, ForeignKey("failure_types.failure_type_id", ondelete="CASCADE", name="fk_pred_type"), nullable=False)
    model_id: Mapped[int] = mapped_column(UInt, ForeignKey("models.model_id", ondelete="RESTRICT", name="fk_pred_model"), nullable=False)
    predicted_for_date: Mapped[date] = mapped_column(Date, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False, comment="calibrated probability 0..1")
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel, values_callable=lambda e: [m.value for m in e]), nullable=False)
    # Populate only for live predictions and a sampled subset of backtests,
    # or this column will dominate the table size.
    feature_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, comment="exact inputs, for reproducibility")
    actual_outcome: Mapped[PredictionOutcome] = mapped_column(Enum(PredictionOutcome, values_callable=lambda e: [m.value for m in e]), nullable=False, default=PredictionOutcome.PENDING, server_default="pending")
    outcome_recorded_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    location: Mapped["Location"] = relationship()


class DailyRanking(Base):
    """The nightly triage list, PERSISTED.

    Looks redundant — you could recompute it. But without stored history you
    cannot measure how much the ranking reorders between storms, and that
    measurement is the proof that this is a tool and not a report.
    """
    __tablename__ = "daily_rankings"
    __table_args__ = (
        UniqueConstraint("city_id", "failure_type_id", "ranking_date", "location_id", "model_id", name="uq_ranking"),
        Index("idx_ranking_date_pos", "ranking_date", "rank_position"),
    )

    ranking_id: Mapped[int] = mapped_column(UBigInt, primary_key=True, autoincrement=True)
    city_id: Mapped[int] = mapped_column(USmallInt, ForeignKey("cities.city_id", ondelete="CASCADE", name="fk_rank_city"), nullable=False)
    failure_type_id: Mapped[int] = mapped_column(UTinyInt, ForeignKey("failure_types.failure_type_id", ondelete="CASCADE", name="fk_rank_type"), nullable=False)
    ranking_date: Mapped[date] = mapped_column(Date, nullable=False)
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_rank_location"), nullable=False)
    rank_position: Mapped[int] = mapped_column(USmallInt, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    model_id: Mapped[int] = mapped_column(UInt, ForeignKey("models.model_id", ondelete="RESTRICT", name="fk_rank_model"), nullable=False)
    in_top_k: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"), comment="was it dispatched to?")
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    location: Mapped["Location"] = relationship()


class EmergingLocation(Base):
    """Sites trending toward failure that are NOT yet on the official register."""
    __tablename__ = "emerging_locations"
    __table_args__ = (
        UniqueConstraint("location_id", "failure_type_id", "detected_at", name="uq_emerging"),
        Index("idx_emerging_status", "status", "detected_at"),
    )

    emerging_id: Mapped[int] = mapped_column(UInt, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE", name="fk_emerging_location"), nullable=False)
    failure_type_id: Mapped[int] = mapped_column(UTinyInt, ForeignKey("failure_types.failure_type_id", ondelete="CASCADE", name="fk_emerging_type"), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    method: Mapped[EmergingMethod] = mapped_column(Enum(EmergingMethod, values_callable=lambda e: [m.value for m in e]), nullable=False)
    trend_statistic: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 5))
    p_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 7))
    changepoint_date: Mapped[Optional[date]] = mapped_column(Date)
    months_of_evidence: Mapped[Optional[int]] = mapped_column(USmallInt)
    status: Mapped[EmergingStatus] = mapped_column(Enum(EmergingStatus, values_callable=lambda e: [m.value for m in e]), nullable=False, default=EmergingStatus.CANDIDATE, server_default="candidate")
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(String(500))

    location: Mapped["Location"] = relationship()
