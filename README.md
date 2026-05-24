# plg_cache_pages — Cache stránek

In-memory TTL cache s admin rozhraním a automatickou invalidací při změně obsahu.

## Admin

`/admin/plg_cache_pages` — statistiky a nastavení:
- **Cache aktivní** — zapne/vypne cache
- **Výchozí TTL** — doba platnosti záznamu v sekundách (výchozí: 300)
- **Maximální počet položek** — hard cap, nejstarší záznamy se vyřadí (výchozí: 500)
- **Statistiky** — počet položek, zásahy, minutí
- **Vymazat cache** — smaže všechny záznamy

## Použití z jiných rozšíření

```python
from src.plugins.plg_cache_pages.cache import page_cache

# Uložit
page_cache.set("/clanky/muj-clanek", rendered_html, ttl=600)

# Číst
cached = page_cache.get("/clanky/muj-clanek")
if cached is None:
    cached = render_page(...)
    page_cache.set("/clanky/muj-clanek", cached)

# Invalidovat konkrétní klíč
page_cache.invalidate("/clanky/muj-clanek")

# Invalidovat prefix
page_cache.invalidate_prefix("/clanky/")
```

## Automatická invalidace

Plugin automaticky vymaže celou cache při hooky:
- `content.article.saved`
- `content.article.deleted`
- `content.page.saved`
- `content.page.deleted`

## Vývoj a testy

```bash
cd plugin/plg_cache_pages
pip install -e ".[dev]"
pytest -q
```
