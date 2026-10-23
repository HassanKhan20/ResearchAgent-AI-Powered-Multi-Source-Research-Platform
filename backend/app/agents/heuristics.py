"""Deterministic, dependency-free fallbacks for each agent step."""

import re
from itertools import combinations

from .state import Claim, Contradiction, Finding

STOPWORDS = set(
    """a an and are as at be been but by can could did do does for from had has have how i if in into is it its
    of on or our so such than that the their them then there these they this to was we were what when where which
    while who whom why will with would you your about also more most many much over under very not no never""".split()
)
NEGATIONS = {"not", "no", "never", "cannot", "isn't", "wasn't", "aren't", "doesn't", "didn't", "neither", "nor"}
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_NUMBER = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")
_WORD = re.compile(r"[a-z][a-z'\-]+")
_MEASURE = re.compile(r"(?<![\d,.])(\d[\d,]*(?:\.\d+)?)\s*(?:(percent)(?![a-z])|(%)|([a-z]+))")


def keywords(text: str) -> list[str]:
    out: list[str] = []
    for w in _WORD.findall(text.lower()):
        if w not in STOPWORDS and len(w) > 2 and w not in out:
            out.append(w)
    return out


def _tokens(text: str) -> set[str]:
    return {w for w in keywords(text) if w not in NEGATIONS}


def _numbers(text: str) -> set[str]:
    # Ignore 4-digit years so "built in 1368" doesn't clash with a length figure.
    return {n.replace(",", "") for n in _NUMBER.findall(text) if not re.fullmatch(r"1[0-9]{3}|20[0-9]{2}", n)}


def _measures(text: str) -> dict[str, set[str]]:
    """Map unit word -> numbers, e.g. "21,196 kilometres" -> {"kilometres": {"21196"}}."""
    out: dict[str, set[str]] = {}
    for num, pct, sym, unit in _MEASURE.findall(text.lower()):
        if re.fullmatch(r"1[0-9]{3}|20[0-9]{2}", num):
            continue
        out.setdefault("percent" if (pct or sym) else unit, set()).add(num.replace(",", ""))
    return out


def _negated(text: str) -> bool:
    return bool(NEGATIONS & set(re.findall(r"[a-z']+", text.lower())))


def jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


# --- planner -----------------------------------------------------------------


def plan_queries(question: str, limit: int) -> list[str]:
    kws = keywords(question)
    candidates = [" ".join(kws[:6]), question.strip().rstrip("?"), " ".join(kws[:3])]
    candidates += [f"{kws[0]} {k}" for k in kws[1:4]] if kws else []
    seen: list[str] = []
    for c in candidates:
        c = c.strip()
        if c and c.lower() not in (s.lower() for s in seen):
            seen.append(c)
    return seen[:limit] or [question]


def broaden_queries(question: str, previous: list[str]) -> list[str]:
    kws = keywords(question)
    fresh = [k for k in kws if k not in previous][:3]
    return fresh or kws[:2] or [question]


# --- extractor ---------------------------------------------------------------


def extract_claims(question: str, sources: list[dict], per_source: int = 4) -> list[Claim]:
    q = set(keywords(question))
    claims: list[Claim] = []
    for idx, src in enumerate(sources, start=1):
        sentences = [s.strip() for s in _SENTENCE.split(src.get("content") or src.get("snippet", "")) if 25 <= len(s.strip()) <= 400]
        ranked = sorted(sentences, key=lambda s: -len(q & set(keywords(s))))
        picked = [s for s in ranked if q & set(keywords(s))][:per_source] or ranked[:2]
        for s in picked:
            claims.append(Claim(id=len(claims) + 1, text=s, source=idx))
    return claims


# --- cross-checker -----------------------------------------------------------


def cross_check(claims: list[Claim], sources: list[dict]) -> tuple[list[Finding], list[Contradiction]]:
    parent = {c.id: c.id for c in claims}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    contradictions: list[Contradiction] = []
    contested: set[int] = set()
    for a, b in combinations(claims, 2):
        if a.source == b.source:
            continue
        sim = jaccard(a.text, b.text)
        ma, mb = _measures(a.text), _measures(b.text)
        shared_units = set(ma) & set(mb)
        # Same unit, different value, and talking about the same subject -> conflicting figures.
        numeric_clash = sim >= 0.1 and any(not (ma[u] & mb[u]) for u in shared_units)
        if sim < 0.3 and not numeric_clash:
            continue
        if not numeric_clash and not shared_units:
            na, nb = _numbers(a.text), _numbers(b.text)
            numeric_clash = bool(na and nb and not (na & nb))
        negation_clash = _negated(a.text) != _negated(b.text) and sim >= 0.4
        if numeric_clash or negation_clash:
            if _already_flagged(contradictions, a, b):
                contested.update((a.id, b.id))
                continue
            cred_a = sources[a.source - 1].get("credibility", 0.5)
            cred_b = sources[b.source - 1].get("credibility", 0.5)
            likely = "a" if cred_a - cred_b > 0.1 else "b" if cred_b - cred_a > 0.1 else "unclear"
            shared = _tokens(a.text) & _tokens(b.text)
            topic = " ".join([w for w in keywords(a.text) if w in shared][:5])
            kind = "different figures" if numeric_clash else "opposite conclusions"
            contradictions.append(
                Contradiction(
                    topic=topic or "conflicting statements",
                    claim_a=a.text,
                    source_a=a.source,
                    claim_b=b.text,
                    source_b=b.source,
                    explanation=f"Sources report {kind} for the same point.",
                    likely_correct=likely,
                )
            )
            contested.update((a.id, b.id))
        else:
            parent[find(a.id)] = find(b.id)

    clusters: dict[int, list[Claim]] = {}
    for c in claims:
        clusters.setdefault(find(c.id), []).append(c)

    findings: list[Finding] = []
    for members in clusters.values():
        best = max(members, key=lambda c: (sources[c.source - 1].get("credibility", 0.5), -len(c.text)))
        srcs = sorted({c.source for c in members})
        if any(c.id in contested for c in members):
            status = "contested"
        elif len(srcs) >= 2:
            status = "corroborated"
        else:
            status = "single-source"
        findings.append(Finding(statement=best.text, sources=srcs, status=status))

    order = {"corroborated": 0, "contested": 1, "single-source": 2}
    findings.sort(key=lambda f: (order[f.status], -len(f.sources)))
    return findings, contradictions


def _already_flagged(existing: list[Contradiction], a: Claim, b: Claim) -> bool:
    """True if an equivalent disagreement (same side restated by another source) is already listed."""
    for c in existing:
        for x, y in ((c.claim_a, c.claim_b), (c.claim_b, c.claim_a)):
            if (x == a.text and jaccard(y, b.text) >= 0.3) or (x == b.text and jaccard(y, a.text) >= 0.3):
                return True
            if jaccard(x, a.text) >= 0.3 and y == b.text or jaccard(x, b.text) >= 0.3 and y == a.text:
                return True
    return False


# --- scoring + writer --------------------------------------------------------

STATUS_WEIGHT = {"corroborated": 1.0, "single-source": 0.55, "contested": 0.25}


def confidence_score(findings: list[dict], sources: list[dict]) -> float:
    if not findings or not sources:
        return 0.0
    agreement = sum(STATUS_WEIGHT[f["status"]] for f in findings) / len(findings)
    credibility = sum(s.get("credibility", 0.5) for s in sources) / len(sources)
    diversity = min(1.0, len({s["provider"] for s in sources}) / 3)
    return round(100 * (0.6 * agreement + 0.3 * credibility + 0.1 * diversity), 1)


def _cite(ids: list[int]) -> str:
    return "".join(f"[{i}]" for i in ids)


def write_report(question: str, findings: list[dict], contradictions: list[dict], sources: list[dict]) -> dict:
    corroborated = [f for f in findings if f["status"] == "corroborated"]
    single = [f for f in findings if f["status"] == "single-source"]
    lead = (corroborated or findings or [{"statement": "No reliable evidence was found.", "sources": []}])[0]
    summary = f"{lead['statement']} {_cite(lead['sources'])}".strip()

    lines = [f"## Answer", "", summary, ""]
    if corroborated:
        lines += ["## Key findings", ""]
        lines += [f"- {f['statement']} {_cite(f['sources'])}" for f in corroborated[:8]]
        lines.append("")
    if contradictions:
        lines += ["## Where sources disagree", ""]
        for c in contradictions:
            verdict = {
                "a": f"The more credible source [{c['source_a']}] is likely correct.",
                "b": f"The more credible source [{c['source_b']}] is likely correct.",
                "unclear": "Neither source is clearly more reliable; verify independently.",
            }[c["likely_correct"]]
            lines += [
                f"- **{c['topic'].capitalize()}**: one source says \"{c['claim_a']}\" [{c['source_a']}], "
                f"while another says \"{c['claim_b']}\" [{c['source_b']}]. {verdict}"
            ]
        lines.append("")
    if single:
        lines += ["## Single-source claims", "", "_Reported by only one source. Treat with caution._", ""]
        lines += [f"- {f['statement']} {_cite(f['sources'])}" for f in single[:6]]
        lines.append("")
    providers = sorted({s["provider"] for s in sources})
    lines += [
        "## Method",
        "",
        f"Searched {len(providers)} source type(s) ({', '.join(providers)}), read {len(sources)} documents, "
        f"extracted claims and cross-checked them pairwise. {len(corroborated)} finding(s) were corroborated "
        f"and {len(contradictions)} contradiction(s) were flagged.",
    ]
    return {"title": question.strip().rstrip("?") + "?", "summary": summary, "markdown": "\n".join(lines)}
