from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .cache import page_cache
from .models import CacheSettings


async def get_or_create_settings(db: AsyncSession) -> CacheSettings:
    s = (
        await db.execute(select(CacheSettings).where(CacheSettings.id == 1))
    ).scalar_one_or_none()
    if s is None:
        s = CacheSettings(id=1)
        db.add(s)
        await db.commit()
        await db.refresh(s)
    return s


async def save_settings(
    db: AsyncSession,
    *,
    enabled: bool,
    default_ttl: int,
    max_entries: int,
) -> CacheSettings:
    s = await get_or_create_settings(db)
    s.enabled = enabled
    s.default_ttl = max(1, default_ttl)
    s.max_entries = max(1, max_entries)
    s.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(s)
    page_cache.reconfigure(default_ttl=s.default_ttl, max_entries=s.max_entries)
    return s


async def apply_settings_to_cache(db: AsyncSession) -> None:
    s = await get_or_create_settings(db)
    page_cache.reconfigure(default_ttl=s.default_ttl, max_entries=s.max_entries)
    if not s.enabled:
        page_cache.clear()
