from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.admin.deps import CurrentAdminUser
from src.api.admin.render import admin_render
from src.core.acl import require_admin_permission
from src.database.base import get_db_session

from .cache import page_cache
from .service import get_or_create_settings, save_settings

router = APIRouter(prefix="/admin/plg_cache_pages", tags=["plg_cache_pages"])


@router.get("", response_class=HTMLResponse)
async def index(
    request: Request,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("cache.manage")),
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    settings = await get_or_create_settings(db)
    stats = page_cache.stats()
    flash = request.session.pop("flash", None)
    return await admin_render(
        "admin/plg_cache_pages/index.html",
        request,
        db,
        user=current_user,
        settings=settings,
        stats=stats,
        flash=flash,
    )


@router.post("", response_class=HTMLResponse)
async def save(
    request: Request,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("cache.manage")),
    db: AsyncSession = Depends(get_db_session),
    enabled: str | None = Form(None),
    default_ttl: int = Form(300),
    max_entries: int = Form(500),
) -> RedirectResponse:
    await save_settings(
        db,
        enabled=enabled is not None,
        default_ttl=default_ttl,
        max_entries=max_entries,
    )
    request.session["flash"] = {"type": "success", "text": "Nastavení uloženo."}
    return RedirectResponse("/admin/plg_cache_pages", status_code=303)


@router.post("/clear", response_class=HTMLResponse)
async def clear(
    request: Request,
    current_user: CurrentAdminUser,
    _acl: object = Depends(require_admin_permission("cache.manage")),
    db: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    count = page_cache.clear()
    request.session["flash"] = {
        "type": "success",
        "text": f"Cache vymazána ({count} položek).",
    }
    return RedirectResponse("/admin/plg_cache_pages", status_code=303)
