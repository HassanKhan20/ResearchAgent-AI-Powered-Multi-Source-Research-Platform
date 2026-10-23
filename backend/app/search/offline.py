"""Deterministic offline corpus.

Used by the test suite and when OFFLINE_MODE=true so the whole agent graph can run
without network access. The documents deliberately disagree on a couple of facts so
the cross-checker has something to flag.
"""

from .base import SearchResult

_CORPUS = [
    SearchResult(
        title="Great Wall of China",
        url="https://en.wikipedia.org/wiki/Great_Wall_of_China",
        provider="wikipedia",
        snippet="The Great Wall of China is a series of fortifications built across the historical northern borders of ancient Chinese states.",
        content=(
            "The Great Wall of China is a series of fortifications built across the historical northern borders of ancient Chinese states. "
            "The best-known sections were built by the Ming dynasty between 1368 and 1644. "
            "A 2012 archaeological survey by the State Administration of Cultural Heritage measured the total length of all wall sections at 21,196 kilometres. "
            "The wall is not visible to the naked eye from low Earth orbit under most conditions."
        ),
        credibility=0.75,
    ),
    SearchResult(
        title="How long is the Great Wall? Survey results",
        url="https://www.ncha.gov.cn/great-wall-survey",
        provider="web",
        snippet="China's national heritage administration reported the wall measures 21,196 kilometres in total length.",
        content=(
            "China's national heritage administration reported the Great Wall measures 21,196 kilometres in total length across 15 provinces. "
            "Most of the surviving wall was built by the Ming dynasty between 1368 and 1644. "
            "Roughly 30 percent of the Ming-era wall has disappeared due to erosion and human activity."
        ),
        credibility=0.9,
    ),
    SearchResult(
        title="Great Wall myths, debunked",
        url="https://www.example-travel-blog.com/great-wall-myths",
        provider="web",
        snippet="Contrary to popular belief, the Great Wall is about 8,850 kilometres long and is visible from space.",
        content=(
            "Contrary to popular belief, the Great Wall is about 8,850 kilometres long. "
            "The Great Wall is visible to the naked eye from low Earth orbit on a clear day. "
            "Most of the surviving wall was built by the Ming dynasty."
        ),
        credibility=0.55,
    ),
    SearchResult(
        title="Remote sensing of linear structures from orbit",
        url="https://arxiv.org/abs/2101.00001",
        provider="arxiv",
        snippet="We evaluate astronaut photography and find that the Great Wall is not visible to the naked eye from low Earth orbit.",
        content=(
            "We evaluate astronaut photography and orbital imagery of large linear structures. "
            "We find that the Great Wall is not visible to the naked eye from low Earth orbit because its width rarely exceeds 6 metres. "
            "Highways and airports are more easily identified than the wall."
        ),
        credibility=0.9,
    ),
]


class OfflineProvider:
    name = "offline"

    async def search(self, query: str, limit: int = 3) -> list[SearchResult]:
        terms = {t for t in query.lower().split() if len(t) > 3}
        scored = sorted(
            _CORPUS,
            key=lambda doc: -sum(t in doc.content.lower() for t in terms),
        )
        return [doc.model_copy() for doc in scored[: limit + 1]]
