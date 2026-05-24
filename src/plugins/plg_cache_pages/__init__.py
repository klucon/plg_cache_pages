from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.registry import ComponentRegistry

_PLUGIN_DIR = Path(__file__).parent


def setup(registry: ComponentRegistry) -> None:
    from jinja2 import FileSystemLoader
    from src.core.hooks import hooks
    from src.core.templates import admin_templates
    from src.i18n.translator import translator

    from src.plugins.plg_cache_pages import admin
    from src.plugins.plg_cache_pages.cache import page_cache

    templates_dir = _PLUGIN_DIR / "templates"
    if templates_dir.is_dir():
        loaders = getattr(admin_templates.loader, "loaders", [])
        if not any(
            isinstance(ldr, FileSystemLoader) and str(templates_dir) in ldr.searchpath
            for ldr in loaders
        ):
            loaders.append(FileSystemLoader(str(templates_dir)))

    async def _on_content_change(**kwargs: object) -> None:
        page_cache.invalidate_prefix("/")

    hooks.on("content.article.saved", _on_content_change)
    hooks.on("content.article.deleted", _on_content_change)
    hooks.on("content.page.saved", _on_content_change)
    hooks.on("content.page.deleted", _on_content_change)

    registry.register_router(admin.router)
    translator.load_domain("plg_cache_pages", _PLUGIN_DIR / "i18n")
