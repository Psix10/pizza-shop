from __future__ import annotations

from datetime import datetime, UTC

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db import Base


class SupportThread(Base):
    __tablename__ = "support_threads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    order_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list["SupportMessage"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
    )


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("support_threads.id"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sender_role: Mapped[str] = mapped_column(String(30), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    is_read: Mapped[bool] = mapped_column(default=False, nullable=False)

    thread: Mapped["SupportThread"] = relationship(back_populates="messages")