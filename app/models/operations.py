"""Interventions, their measured effects, alerts and actions taken."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    ActionStatus, AlertSeverity, AlertStatus, AlertType, EffectVerdict,
    InterventionType, TargetRole,
)
from app.models.types import UBigInt, UInt, USmallInt, UTinyInt


class Intervention(Base):
    """A fix the city applied. The input to 'did it work?'"""
    __tablename__ = "interventions"
    __table_args__ = (Index("idx_intervention_loc_date", "location_id", "start_date"),)

    intervention_id: Mapped[int] = mapped_column(UInt, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE"), nullable=False)
    failure_type_id: Mapped[Optional[int]] = mapped_column(UTinyInt)
    intervention_type: Mapped[InterventionType] = mapped_column(Enum(InterventionType, values_callable=lambda e: [m.value for m in e]), nullable=False)
    agency: Mapped[Optional[str]] = mapped_column(String(120))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    cost_inr: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    external_ref: Mapped[Optional[str]] = mapped_column(String(120))
    source_id: Mapped[Optional[int]] = mapped_column(USmallInt, ForeignKey("data_sources.source_id", ondelete="SET NULL"))

    location: Mapped["Location"] = relationship()


class InterventionEffect(Base):
    """Difference-in-differences: treated site before/after against untreated
    sites with similar history over the same window. The control arm matters —
    a dry year makes every intervention look effective."""
    __tablename__ = "intervention_effects"
    __table_args__ = (UniqueConstraint("intervention_id", "evaluated_at", "window_months", name="uq_effect"),)

    effect_id: Mapped[int] = mapped_column(UInt, primary_key=True, autoincrement=True)
    intervention_id: Mapped[int] = mapped_column(UInt, ForeignKey("interventions.intervention_id", ondelete="CASCADE"), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_months: Mapped[int] = mapped_column(USmallInt, nullable=False)
    treated_pre_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 5))
    treated_post_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 5))
    control_pre_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 5))
    control_post_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 5))
    control_n: Mapped[Optional[int]] = mapped_column(USmallInt)
    did_estimate: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 5))
    p_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 7))
    verdict: Mapped[EffectVerdict] = mapped_column(Enum(EffectVerdict, values_callable=lambda e: [m.value for m in e]), nullable=False, default=EffectVerdict.INCONCLUSIVE)

    intervention: Mapped["Intervention"] = relationship()


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("idx_alert_status", "alert_status", "created_at"),
        Index("idx_alert_city", "city_id", "created_at"),
    )

    alert_id: Mapped[int] = mapped_column(UBigInt, primary_key=True, autoincrement=True)
    prediction_id: Mapped[Optional[int]] = mapped_column(UBigInt, ForeignKey("risk_predictions.prediction_id", ondelete="CASCADE"))
    emerging_id: Mapped[Optional[int]] = mapped_column(UInt, ForeignKey("emerging_locations.emerging_id", ondelete="CASCADE"))
    city_id: Mapped[int] = mapped_column(USmallInt, ForeignKey("cities.city_id", ondelete="CASCADE"), nullable=False)
    target_role: Mapped[TargetRole] = mapped_column(Enum(TargetRole, values_callable=lambda e: [m.value for m in e]), nullable=False, default=TargetRole.OFFICER)
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType, values_callable=lambda e: [m.value for m in e]), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity, values_callable=lambda e: [m.value for m in e]), nullable=False, default=AlertSeverity.WARNING)
    alert_message: Mapped[str] = mapped_column(Text, nullable=False)
    alert_status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus, values_callable=lambda e: [m.value for m in e]), nullable=False, default=AlertStatus.QUEUED)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class AlertRecipient(Base):
    __tablename__ = "alert_recipients"

    alert_id: Mapped[int] = mapped_column(UBigInt, ForeignKey("alerts.alert_id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(UInt, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, index=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class PreventiveAction(Base):
    __tablename__ = "preventive_actions"
    __table_args__ = (Index("idx_action_loc_date", "location_id", "action_date"),)

    action_id: Mapped[int] = mapped_column(UBigInt, primary_key=True, autoincrement=True)
    prediction_id: Mapped[Optional[int]] = mapped_column(UBigInt, ForeignKey("risk_predictions.prediction_id", ondelete="SET NULL"))
    location_id: Mapped[int] = mapped_column(UInt, ForeignKey("locations.location_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(UInt, ForeignKey("users.user_id", ondelete="SET NULL"))
    department: Mapped[Optional[str]] = mapped_column(String(120))
    action_taken: Mapped[Optional[str]] = mapped_column(Text)
    action_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ActionStatus] = mapped_column(Enum(ActionStatus, values_callable=lambda e: [m.value for m in e]), nullable=False, default=ActionStatus.PLANNED)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
