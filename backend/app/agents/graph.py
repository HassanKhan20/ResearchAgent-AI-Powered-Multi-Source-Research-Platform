r"""LangGraph research pipeline.

    plan -> search --(too few sources?)--> refine -> search
                  \-> extract -> verify -> write -> END

Each node tries Claude first and falls back to the heuristics module, and reports
progress through the `emit` callback so the UI can render a live timeline.
"""

import json
from collections.abc import Awaitable, Callable
from typing import Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from ..config import get_settings
from ..search.base import SearchProvider
from ..search.hub import multi_search
from . import heuristics as h
from .llm import structured
from .state import Claim, Contradiction, Finding, ResearchState

Emit = Callable[[str, str, dict], Awaitable[None]]


async def _noop(node: str, status: str, data: dict) -> None:
    return None


# --- LLM output schemas --------------------------------------------------------


class PlanOut(BaseModel):
    sub_queries: list[str] = Field(description="Short keyword search queries, 2-6 words each")


class ClaimOut(BaseModel):
    text: str = Field(description="One atomic, checkable factual statement")
    source: int = Field(description="1-based source number the claim came from")


class ClaimsOut(BaseModel):
    claims: list[ClaimOut]


class FindingOut(BaseModel):
    statement: str
    claim_ids: list[int]
    status: Literal["corroborated", "single-source", "contested"]


class ContradictionOut(BaseModel):
    topic: str
    claim_a_id: int
    claim_b_id: int
    explanation: str
    likely_correct: Literal["a", "b", "unclear"]


class VerifyOut(BaseModel):
    findings: list[FindingOut]
    contradictions: list[ContradictionOut]


class ReportOut(BaseModel):
    title: str
    summary: str = Field(description="2-3 sentence direct answer with [n] citations")
    markdown: str = Field(description="Full report body in Markdown with [n] citations")


def _source_digest(sources: list[dict], chars: int = 2500) -> str:
    return "\n\n".join(
        f"[{i}] {s['title']} ({s['provider']}, credibility {s['credibility']:.2f})\n{(s.get('content') or s['snippet'])[:chars]}"
        for i, s in enumerate(sources, start=1)
    )


# --- graph -------------------------------------------------------------------


def build_graph(emit: Emit = _noop, providers: list[SearchProvider] | None = None):
    settings = get_settings()

    async def plan(state: ResearchState) -> ResearchState:
        await emit("plan", "started", {})
        q = state["question"]
        out = await structured(
            "You are a research planner. Break the user's question into focused web/encyclopedia/paper search queries "
            "that together cover the facts needed to answer it, including queries likely to surface disagreement.",
            f"Question: {q}\nReturn at most {settings.max_sub_queries} queries.",
            PlanOut,
            max_tokens=2000,
        )
        queries = (out.sub_queries if out else h.plan_queries(q, settings.max_sub_queries))[: settings.max_sub_queries]
        await emit("plan", "completed", {"sub_queries": queries})
        return {"sub_queries": queries, "round": 0}

    async def search(state: ResearchState) -> ResearchState:
        await emit("search", "started", {"queries": state["sub_queries"]})
        found = await multi_search(state["sub_queries"], providers)
        merged = {s["url"]: s for s in state.get("sources", [])}
        for r in found:
            merged.setdefault(r.url, r.model_dump())
        sources = sorted(merged.values(), key=lambda s: -s["credibility"])[: settings.max_sources]
        await emit(
            "search",
            "completed",
            {
                "count": len(sources),
                "providers": sorted({s["provider"] for s in sources}),
                "sources": [{"title": s["title"], "url": s["url"], "provider": s["provider"]} for s in sources],
            },
        )
        return {"sources": sources}

    def needs_refine(state: ResearchState) -> str:
        if len(state.get("sources", [])) < 3 and state.get("round", 0) < settings.max_refine_rounds:
            return "refine"
        return "extract"

    async def refine(state: ResearchState) -> ResearchState:
        queries = h.broaden_queries(state["question"], state["sub_queries"])
        await emit("refine", "completed", {"reason": "too few sources", "sub_queries": queries})
        return {"sub_queries": queries, "round": state.get("round", 0) + 1}

    async def extract(state: ResearchState) -> ResearchState:
        await emit("extract", "started", {})
        sources = state["sources"]
        claims: list[Claim] = []
        if sources:
            out = await structured(
                "You extract atomic factual claims from sources. Only include claims relevant to the question, "
                "quote numbers exactly, and attribute each claim to the single source it came from.",
                f"Question: {state['question']}\n\nSources:\n{_source_digest(sources)}\n\n"
                "Extract up to 4 relevant claims per source.",
                ClaimsOut,
            )
            if out:
                claims = [
                    Claim(id=i, text=c.text, source=c.source)
                    for i, c in enumerate(out.claims, start=1)
                    if 1 <= c.source <= len(sources)
                ]
            if not claims:
                claims = h.extract_claims(state["question"], sources)
        await emit("extract", "completed", {"count": len(claims)})
        return {"claims": [c.model_dump() for c in claims]}

    async def verify(state: ResearchState) -> ResearchState:
        await emit("verify", "started", {})
        claims = [Claim(**c) for c in state["claims"]]
        sources = state["sources"]
        by_id = {c.id: c for c in claims}
        findings: list[Finding] = []
        contradictions: list[Contradiction] = []

        out = None
        if claims:
            listing = "\n".join(
                f"#{c.id} (source [{c.source}], credibility {sources[c.source - 1]['credibility']:.2f}): {c.text}" for c in claims
            )
            out = await structured(
                "You are a fact-checker. Group claims that state the same fact into findings. A finding is "
                "'corroborated' if two or more distinct sources support it, 'single-source' if only one does, and "
                "'contested' if sources disagree. List every pair of claims that contradict each other and say which "
                "is more likely correct based on source credibility and specificity.",
                f"Question: {state['question']}\n\nClaims:\n{listing}",
                VerifyOut,
            )
        if out:
            for f in out.findings:
                ids = [by_id[i].source for i in f.claim_ids if i in by_id]
                if ids:
                    findings.append(Finding(statement=f.statement, sources=sorted(set(ids)), status=f.status))
            for c in out.contradictions:
                a, b = by_id.get(c.claim_a_id), by_id.get(c.claim_b_id)
                if a and b:
                    contradictions.append(
                        Contradiction(
                            topic=c.topic,
                            claim_a=a.text,
                            source_a=a.source,
                            claim_b=b.text,
                            source_b=b.source,
                            explanation=c.explanation,
                            likely_correct=c.likely_correct,
                        )
                    )
        if not findings:
            findings, contradictions = h.cross_check(claims, sources)

        f_dicts = [f.model_dump() for f in findings]
        confidence = h.confidence_score(f_dicts, sources)
        await emit(
            "verify",
            "completed",
            {
                "corroborated": sum(f.status == "corroborated" for f in findings),
                "single_source": sum(f.status == "single-source" for f in findings),
                "contested": sum(f.status == "contested" for f in findings),
                "contradictions": len(contradictions),
                "confidence": confidence,
            },
        )
        return {"findings": f_dicts, "contradictions": [c.model_dump() for c in contradictions], "confidence": confidence}

    async def write(state: ResearchState) -> ResearchState:
        await emit("write", "started", {})
        payload = {
            "question": state["question"],
            "findings": state["findings"],
            "contradictions": state["contradictions"],
            "sources": [{"n": i, "title": s["title"], "provider": s["provider"]} for i, s in enumerate(state["sources"], start=1)],
        }
        out = None
        if state["findings"]:
            out = await structured(
                "You write concise, trustworthy research reports. Use ONLY the verified findings provided. Cite every "
                "sentence with source numbers like [2] or [1][3]. Start with '## Answer', then '## Key findings', then "
                "'## Where sources disagree' if there are contradictions (explain both sides and which is more likely "
                "correct), then '## Single-source claims' for unverified points. Never invent sources.",
                json.dumps(payload, ensure_ascii=False),
                ReportOut,
            )
        report = out.model_dump() if out else h.write_report(state["question"], state["findings"], state["contradictions"], state["sources"])
        await emit("write", "completed", {"title": report["title"]})
        return {"report": report}

    g = StateGraph(ResearchState)
    g.add_node("plan", plan)
    g.add_node("search", search)
    g.add_node("refine", refine)
    g.add_node("extract", extract)
    g.add_node("verify", verify)
    g.add_node("write", write)
    g.add_edge(START, "plan")
    g.add_edge("plan", "search")
    g.add_conditional_edges("search", needs_refine, {"refine": "refine", "extract": "extract"})
    g.add_edge("refine", "search")
    g.add_edge("extract", "verify")
    g.add_edge("verify", "write")
    g.add_edge("write", END)
    return g.compile()


async def run_research(question: str, emit: Emit = _noop, providers: list[SearchProvider] | None = None) -> ResearchState:
    graph = build_graph(emit, providers)
    return await graph.ainvoke({"question": question, "sources": []})
