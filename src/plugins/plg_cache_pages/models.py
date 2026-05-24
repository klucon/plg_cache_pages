from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from src.database.base import Base


def _now() -> datetime:
    return datetime.now(UTC)


class CacheSettings(Base):
    __tablename__ = "plg_cache_pages_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_ttl: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    max_entries: Mapped[int] = mapped_column(Integer, default=500, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
