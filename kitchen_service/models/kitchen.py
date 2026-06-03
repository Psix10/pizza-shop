from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.db import Base


class KitchenJob(Base):
    __tablename__ = "kitchen_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    store_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    address_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    priority_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued")
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)