from app.agents.graph import run_research


async def test_pipeline_produces_cited_report_and_flags_contradictions():
    events = []

    async def emit(node, status, data):
        events.append((node, status))

    state = await run_research("How long is the Great Wall of China and is it visible from space?", emit)

    assert [n for n, s in events if s == "completed"] == ["plan", "search", "extract", "verify", "write"]
    assert len(state["sources"]) >= 3
    assert state["contradictions"], "offline corpus contains conflicting claims"
    assert any(f["status"] == "corroborated" for f in state["findings"])
    assert "[1]" in state["report"]["markdown"]
    assert 0 < state["confidence"] <= 100


async def test_refine_loop_runs_when_search_is_thin():
    calls = []

    class ThinProvider:
        name = "thin"

        async def search(self, query, limit=3):
            calls.append(query)
            return []

    events = []

    async def emit(node, status, data):
        events.append(node)

    state = await run_research("An obscure question about nothing at all", emit, providers=[ThinProvider()])
    assert "refine" in events
    assert state["report"]["markdown"]
