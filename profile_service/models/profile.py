# models/profile.py
from datetime import date

from sqlalchemy import (
    BigInteger,
    String,
    Date,
    DateTime,
    Boolean,
    Numeric,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db import Base


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )

    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    messenger: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    addresses: Mapped[list["Address"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    house: Mapped[str] = mapped_column(String(50), nullable=False)
    apartment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entrance: Mapped[str | None] = mapped_column(String(50), nullable=True)
    floor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    door_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    profile: Mapped["Profile"] = relationship(
        back_populates="addresses",
        lazy="joined",
    )