from app.agents.heuristics import confidence_score, cross_check, extract_claims, plan_queries
from app.agents.state import Claim


def test_plan_queries_dedupes_and_limits():
    queries = plan_queries("What causes the northern lights to appear?", 3)
    assert 1 <= len(queries) <= 3
    assert len({q.lower() for q in queries}) == len(queries)


def test_extract_claims_prefers_relevant_sentences():
    sources = [{"content": "Cats are mammals. The aurora borealis is caused by solar wind hitting the magnetosphere. Pizza is tasty food."}]
    claims = extract_claims("What causes the aurora borealis?", sources)
    assert any("solar wind" in c.text for c in claims)
    assert all("Pizza" not in c.text for c in claims)


def test_cross_check_flags_numeric_and_negation_conflicts():
    sources = [{"credibility": 0.9}, {"credibility": 0.5}, {"credibility": 0.9}]
    claims = [
        Claim(id=1, text="The bridge spans 1,280 metres across the strait.", source=1),
        Claim(id=2, text="The bridge spans 900 metres across the strait.", source=2),
        Claim(id=3, text="The bridge spans 1,280 metres across the strait and opened to traffic.", source=3),
        Claim(id=4, text="The bridge is not visible from the nearby city centre.", source=1),
        Claim(id=5, text="The bridge is visible from the nearby city centre.", source=2),
    ]
    findings, contradictions = cross_check(claims, sources)
    pairs = {(c.source_a, c.source_b) for c in contradictions}
    assert any({1, 2} == set(p) or {3, 2} == set(p) for p in pairs)
    assert any(c.likely_correct in ("a", "b") for c in contradictions)
    statuses = {f.status for f in findings}
    assert "contested" in statuses


def test_corroboration_raises_confidence():
    sources = [{"credibility": 0.9, "provider": "wikipedia"}, {"credibility": 0.9, "provider": "arxiv"}]
    strong = confidence_score([{"status": "corroborated"}], sources)
    weak = confidence_score([{"status": "contested"}], sources)
    assert strong > weak > 0
