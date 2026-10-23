import asyncio
import logging

from ..cache import cache_key, get_cache
from ..config import get_settings
from .base import SearchProvider, SearchResult
from .offline import OfflineProvider
from .providers import ArxivProvider, TavilyProvider, WikipediaProvider

log = logging.getLogger(__name__)


def default_providers() -> list[SearchProvider]:
    settings = get_settings()
    if settings.offline_mode:
        return [OfflineProvider()]
    providers: list[SearchProvider] = [WikipediaProvider(), ArxivProvider()]
    if settings.tavily_api_key:
        providers.insert(0, TavilyProvider(settings.tavily_api_key))
    return providers


async def _cached_search(provider: SearchProvider, query: str, limit: int) -> list[SearchResult]:
    cache = get_cache()
    key = cache_key("search", provider.name, query.lower().strip(), str(limit))
    if (hit := await cache.get_json(key)) is not None:
        return [SearchResult(**r) for r in hit]
    try:
        results = await provider.search(query, limit)
    except Exception as exc:  # one flaky provider must not sink the run
        log.warning("provider %s failed for %r: %s", provider.name, query, exc)
        return []
    await cache.set_json(key, [r.model_dump() for r in results], ttl=get_settings().search_cache_ttl)
    return results


async def multi_search(
    queries: list[str], providers: list[SearchProvider] | None = None, limit: int = 3
) -> list[SearchResult]:
    """Fan every query out to every provider in parallel and de-duplicate by URL."""
    providers = providers or default_providers()
    batches = await asyncio.gather(*(_cached_search(p, q, limit) for q in queries for p in providers))
    seen: dict[str, SearchResult] = {}
    for batch in batches:
        for result in batch:
            seen.setdefault(result.url.rstrip("/"), result)
    return sorted(seen.values(), key=lambda r: -r.credibility)
