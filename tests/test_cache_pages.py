from __future__ import annotations

import time

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.plugins.plg_cache_pages.cache import PageCache, page_cache
from src.plugins.plg_cache_pages.service import get_or_create_settings, save_settings

# ---------------------------------------------------------------------------
# PageCache unit tests (no DB needed)
# ---------------------------------------------------------------------------


def test_cache_set_and_get():
    c = PageCache(default_ttl=60)
    c.set("key1", "value1")
    assert c.get("key1") == "value1"


def test_cache_miss_returns_none():
    c = PageCache()
    assert c.get("nonexistent") is None


def test_cache_expiry():
    c = PageCache(default_ttl=60)
    c.set("key", "val", ttl=0)
    time.sleep(0.01)
    assert c.get("key") is None


def test_cache_custom_ttl():
    c = PageCache(default_ttl=1)
    c.set("key", "val", ttl=3600)
    assert c.get("key") == "val"


def test_cache_invalidate():
    c = PageCache()
    c.set("key", "val")
    assert c.invalidate("key") is True
    assert c.get("key") is None


def test_cache_invalidate_missing_returns_false():
    c = PageCache()
    assert c.invalidate("nonexistent") is False


def test_cache_invalidate_prefix():
    c = PageCache()
    c.set("/articles/a", "a")
    c.set("/articles/b", "b")
    c.set("/pages/c", "c")
    removed = c.invalidate_prefix("/articles/")
    assert removed == 2
    assert c.get("/articles/a") is None
    assert c.get("/pages/c") == "c"


def test_cache_clear():
    c = PageCache()
    c.set("a", 1)
    c.set("b", 2)
    removed = c.clear()
    assert removed == 2
    assert c.get("a") is None


def test_cache_max_entries_evicts():
    c = PageCache(max_entries=3)
    c.set("a", 1, ttl=3600)
    c.set("b", 2, ttl=3600)
    c.set("c", 3, ttl=3600)
    c.set("d", 4, ttl=3600)
    assert c.stats()["entries"] == 3


def test_cache_stats():
    c = PageCache()
    c.set("k", "v")
    c.get("k")
    c.get("missing")
    stats = c.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["entries"] == 1


def test_cache_stats_cleared_after_clear():
    c = PageCache()
    c.set("k", "v")
    c.get("k")
    c.clear()
    assert c.stats()["hits"] == 0
    assert c.stats()["misses"] == 0


def test_reconfigure():
    c = PageCache(default_ttl=60, max_entries=100)
    c.reconfigure(default_ttl=120, max_entries=200)
    assert c.default_ttl == 120
    assert c.max_entries == 200


# ---------------------------------------------------------------------------
# service layer
# ---------------------------------------------------------------------------


async def test_get_or_create_defaults(db_session: AsyncSession):
    s = await get_or_create_settings(db_session)
    assert s.id == 1
    assert s.enabled is True
    assert s.default_ttl == 300
    assert s.max_entries == 500


async def test_save_settings(db_session: AsyncSession):
    await save_settings(db_session, enabled=False, default_ttl=60, max_entries=100)
    s = await get_or_create_settings(db_session)
    assert s.enabled is False
    assert s.default_ttl == 60
    assert s.max_entries == 100


async def test_save_settings_reconfigures_cache(db_session: AsyncSession):
    await save_settings(db_session, enabled=True, default_ttl=120, max_entries=200)
    assert page_cache.default_ttl == 120
    assert page_cache.max_entries == 200


# ---------------------------------------------------------------------------
# admin routes
# ---------------------------------------------------------------------------


async def test_admin_requires_auth(client: AsyncClient):
    resp = await client.get("/admin/plg_cache_pages", follow_redirects=False)
    assert resp.status_code in (302, 303)


async def test_admin_index_authenticated(auth_client: AsyncClient):
    resp = await auth_client.get("/admin/plg_cache_pages", follow_redirects=False)
    assert resp.status_code == 200


async def test_admin_save_redirects(auth_client: AsyncClient):
    resp = await auth_client.post(
        "/admin/plg_cache_pages",
        data={"enabled": "on", "default_ttl": "600", "max_entries": "1000"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/admin/plg_cache_pages" in resp.headers["location"]


async def test_admin_save_persists(auth_client: AsyncClient, db_session: AsyncSession):
    await auth_client.post(
        "/admin/plg_cache_pages",
        data={"default_ttl": "120", "max_entries": "50"},
        follow_redirects=False,
    )
    s = await get_or_create_settings(db_session)
    assert s.enabled is False
    assert s.default_ttl == 120
    assert s.max_entries == 50


async def test_admin_clear_redirects(auth_client: AsyncClient):
    page_cache.set("test_key", "test_value")
    resp = await auth_client.post("/admin/plg_cache_pages/clear", follow_redirects=False)
    assert resp.status_code == 303
    assert page_cache.get("test_key") is None


async def test_content_hook_invalidates_cache():
    from src.core.hooks import hooks
    page_cache.set("/articles/test", "<html>test</html>")
    await hooks.fire("content.article.saved")
    assert page_cache.get("/articles/test") is None
