"""Users. Two roles only in rev 2 — admin and officer."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole
from app.models.types import UInt, USmallInt


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(UInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(190), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, values_callable=lambda e: [m.value for m in e]), nullable=False, default=UserRole.OFFICER)
    department: Mapped[Optional[str]] = mapped_column(String(120))
    city_id: Mapped[Optional[int]] = mapped_column(USmallInt, ForeignKey("cities.city_id", ondelete="SET NULL"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    city: Mapped[Optional["City"]] = relationship()

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
