# models/user_session.py
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import BigInteger, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    expires_at: Mapped[sa.DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    revoked_at: Mapped[sa.DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship(back_populates="sessions")