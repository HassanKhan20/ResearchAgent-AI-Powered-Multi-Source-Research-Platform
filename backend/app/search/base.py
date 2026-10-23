from typing import Protocol
from urllib.parse import urlparse

from pydantic import BaseModel

HIGH_TRUST = ("nature.com", "science.org", "nih.gov", "who.int", "arxiv.org", "nasa.gov", "ieee.org", "acm.org")
MEDIUM_TRUST = ("wikipedia.org", "reuters.com", "apnews.com", "bbc.co.uk", "bbc.com", "britannica.com")


class SearchResult(BaseModel):
    title: str
    url: str
    provider: str
    snippet: str
    content: str = ""
    published: str | None = None
    credibility: float = 0.5


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, limit: int = 3) -> list[SearchResult]: ...


def credibility_for(url: str) -> float:
    host = urlparse(url).netloc.lower()
    if host.endswith((".gov", ".edu")) or any(host.endswith(d) for d in HIGH_TRUST):
        return 0.9
    if any(host.endswith(d) for d in MEDIUM_TRUST):
        return 0.75
    return 0.55
