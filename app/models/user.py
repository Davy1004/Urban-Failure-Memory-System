"""Users. Two roles only in rev 2 — admin and officer."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, String, TIMESTAMP,
    UniqueConstraint, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole
from app.models.types import UInt, USmallInt


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("idx_users_city", "city_id"),
    )

    user_id: Mapped[int] = mapped_column(UInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(190), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="bcrypt/argon2 — never store plaintext")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, values_callable=lambda e: [m.value for m in e]), nullable=False, default=UserRole.OFFICER, server_default="officer")
    department: Mapped[Optional[str]] = mapped_column(String(120))
    city_id: Mapped[Optional[int]] = mapped_column(USmallInt, ForeignKey("cities.city_id", ondelete="SET NULL", name="fk_user_city"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("1"))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, onupdate=func.now(),
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    city: Mapped[Optional["City"]] = relationship()

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
