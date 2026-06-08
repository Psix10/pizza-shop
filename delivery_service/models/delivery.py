from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.db import Base


class DeliveryJob(Base):
    __tablename__ = "delivery_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # связь с заказом и точкой
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    store_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    address_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # исполнитель
    courier_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    
    # заказчик
    customer_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    
    # статус доставки:
    # assigned -> on_the_way -> delivered / cancelled
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="assigned",
        index=True,
    )

    # временные метки по жизненному циклу доставки
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    picked_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # приоритизация доставки (см. раздел 7 ТЗ — priority_score)
    priority_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )