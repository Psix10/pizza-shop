from __future__ import annotations

from datetime import time
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    schedules: Mapped[List["StoreSchedule"]] = relationship(
        back_populates="store", cascade="all, delete-orphan"
    )
    delivery_zones: Mapped[List["DeliveryZone"]] = relationship(
        back_populates="store", cascade="all, delete-orphan"
    )
    capacity: Mapped[Optional["StoreCapacity"]] = relationship(
        back_populates="store", uselist=False, cascade="all, delete-orphan"
    )


class StoreSchedule(Base):
    __tablename__ = "store_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"))
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-6
    open_time: Mapped[time] = mapped_column(Time, nullable=False)
    close_time: Mapped[time] = mapped_column(Time, nullable=False)

    store: Mapped["Store"] = relationship(back_populates="schedules")


class DeliveryZone(Base):
    __tablename__ = "delivery_zones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"))
    zone_name: Mapped[str] = mapped_column(String(100), nullable=False)
    polygon_geojson: Mapped[str] = mapped_column(Text, nullable=False)
    min_eta: Mapped[int] = mapped_column(Integer, nullable=False)  # минуты
    max_eta: Mapped[int] = mapped_column(Integer, nullable=False)

    store: Mapped["Store"] = relationship(back_populates="delivery_zones")


class StoreCapacity(Base):
    __tablename__ = "store_capacity"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"))
    max_parallel_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    courier_pool_size: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    store: Mapped["Store"] = relationship(back_populates="capacity")