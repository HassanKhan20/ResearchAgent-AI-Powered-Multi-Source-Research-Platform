import logging
import xml.etree.ElementTree as ET

import httpx

from .base import SearchResult, credibility_for

log = logging.getLogger(__name__)

USER_AGENT = "ResearchAgent/1.0 (https://github.com/HassanKhan20/ResearchAgent-AI-Powered-Multi-Source-Research-Platform)"
TIMEOUT = httpx.Timeout(12.0, connect=6.0)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=True)


class WikipediaProvider:
    name = "wikipedia"

    async def search(self, query: str, limit: int = 3) -> list[SearchResult]:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": limit,
            "prop": "extracts|info",
            "exintro": 1,
            "explaintext": 1,
            "exsentences": 12,
            "inprop": "url",
        }
        async with _client() as client:
            resp = await client.get("https://en.wikipedia.org/w/api.php", params=params)
            resp.raise_for_status()
        pages = (resp.json().get("query") or {}).get("pages") or {}
        results = []
        for page in sorted(pages.values(), key=lambda p: p.get("index", 0)):
            text = (page.get("extract") or "").strip()
            if not text:
                continue
            url = page.get("fullurl") or f"https://en.wikipedia.org/?curid={page['pageid']}"
            results.append(
                SearchResult(
                    title=page["title"],
                    url=url,
                    provider=self.name,
                    snippet=text[:280],
                    content=text,
                    credibility=credibility_for(url),
                )
            )
        return results


class ArxivProvider:
    name = "arxiv"
    _ns = {"a": "http://www.w3.org/2005/Atom"}

    async def search(self, query: str, limit: int = 3) -> list[SearchResult]:
        terms = [t for t in query.replace('"', " ").split() if len(t) > 2][:4] or [query]
        params = {"search_query": " AND ".join(f"all:{t}" for t in terms), "max_results": limit, "sortBy": "relevance"}
        async with _client() as client:
            resp = await client.get("https://export.arxiv.org/api/query", params=params)
            resp.raise_for_status()
        root = ET.fromstring(resp.text)
        results = []
        for entry in root.findall("a:entry", self._ns):
            title = " ".join((entry.findtext("a:title", "", self._ns)).split())
            summary = " ".join((entry.findtext("a:summary", "", self._ns)).split())
            url = entry.findtext("a:id", "", self._ns)
            if not (title and summary and url):
                continue
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    provider=self.name,
                    snippet=summary[:280],
                    content=summary,
                    published=(entry.findtext("a:published", "", self._ns) or None),
                    credibility=credibility_for(url),
                )
            )
        return results


class TavilyProvider:
    name = "web"

    def __init__(self, api_key: str) -> None:
        self._key = api_key

    async def search(self, query: str, limit: int = 3) -> list[SearchResult]:
        async with _client() as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {self._key}"},
                json={"query": query, "max_results": limit, "search_depth": "basic"},
            )
            resp.raise_for_status()
        results = []
        for item in resp.json().get("results", []):
            content = item.get("content") or ""
            results.append(
                SearchResult(
                    title=item.get("title") or item["url"],
                    url=item["url"],
                    provider=self.name,
                    snippet=content[:280],
                    content=content,
                    published=item.get("published_date"),
                    credibility=credibility_for(item["url"]),
                )
            )
        return results
