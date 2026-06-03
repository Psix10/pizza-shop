from sqlalchemy import BigInteger, String, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db import Base
from models.role import Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)

    role_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=True, default="user"
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    role: Mapped["Role"] = relationship()
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )