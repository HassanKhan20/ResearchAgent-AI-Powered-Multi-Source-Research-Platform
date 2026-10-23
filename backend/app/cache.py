"""Cache + event-log abstraction.

Redis is used when REDIS_URL is set; otherwise an in-process store with the same
interface keeps local development dependency-free.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Protocol

from .config import get_settings

log = logging.getLogger(__name__)


class Cache(Protocol):
    async def get_json(self, key: str) -> Any | None: ...
    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def append_event(self, key: str, event: dict, ttl: int = 86400) -> None: ...
    async def read_events(self, key: str, start: int = 0) -> list[dict]: ...
    async def ping(self) -> bool: ...


class MemoryCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float | None]] = {}
        self._lists: dict[str, list[dict]] = {}
        self._lock = asyncio.Lock()

    def _alive(self, key: str) -> bool:
        item = self._data.get(key)
        if item is None:
            return False
        _, expires = item
        if expires is not None and expires < time.monotonic():
            self._data.pop(key, None)
            return False
        return True

    async def get_json(self, key: str) -> Any | None:
        return self._data[key][0] if self._alive(key) else None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        expires = time.monotonic() + ttl if ttl else None
        self._data[key] = (json.loads(json.dumps(value, default=str)), expires)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._lists.pop(key, None)

    async def append_event(self, key: str, event: dict, ttl: int = 86400) -> None:
        async with self._lock:
            self._lists.setdefault(key, []).append(event)

    async def read_events(self, key: str, start: int = 0) -> list[dict]:
        return list(self._lists.get(key, [])[start:])

    async def ping(self) -> bool:
        return True


class RedisCache:
    def __init__(self, url: str) -> None:
        from redis import asyncio as aioredis

        self._r = aioredis.from_url(url, decode_responses=True)

    async def get_json(self, key: str) -> Any | None:
        raw = await self._r.get(key)
        return json.loads(raw) if raw else None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        await self._r.set(key, json.dumps(value, default=str), ex=ttl)

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def append_event(self, key: str, event: dict, ttl: int = 86400) -> None:
        pipe = self._r.pipeline()
        pipe.rpush(key, json.dumps(event, default=str))
        pipe.expire(key, ttl)
        await pipe.execute()

    async def read_events(self, key: str, start: int = 0) -> list[dict]:
        return [json.loads(x) for x in await self._r.lrange(key, start, -1)]

    async def ping(self) -> bool:
        try:
            return bool(await self._r.ping())
        except Exception:
            return False


_cache: Cache | None = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        url = get_settings().redis_url
        _cache = RedisCache(url) if url else MemoryCache()
        log.info("cache backend: %s", type(_cache).__name__)
    return _cache


def set_cache(cache: Cache) -> None:
    global _cache
    _cache = cache


def cache_key(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]
    return f"{parts[0]}:{digest}"
