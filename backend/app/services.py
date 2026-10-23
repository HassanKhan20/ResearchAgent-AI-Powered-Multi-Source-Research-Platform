import logging
import time
from datetime import datetime, timezone

from .agents.graph import run_research
from .cache import get_cache
from .db import SessionLocal
from .models import Report, ResearchJob
from .search.base import SearchProvider

log = logging.getLogger(__name__)


def events_key(job_id: str) -> str:
    return f"job:{job_id}:events"


async def run_job(job_id: str, providers: list[SearchProvider] | None = None) -> None:
    cache = get_cache()
    key = events_key(job_id)

    async def emit(node: str, status: str, data: dict) -> None:
        await cache.append_event(key, {"type": "step", "node": node, "status": status, "data": data, "ts": time.time()})
        # Intermediate state is cached so a reconnecting client can render partial results.
        await cache.set_json(f"job:{job_id}:latest:{node}", data, ttl=86400)

    async with SessionLocal() as db:
        job = await db.get(ResearchJob, job_id)
        if job is None:
            return
        job.status = "running"
        await db.commit()
        await cache.append_event(key, {"type": "status", "status": "running", "ts": time.time()})

        try:
            state = await run_research(job.question, emit, providers)
            report_data = state["report"]
            report = Report(
                job_id=job.id,
                title=report_data["title"][:300],
                summary=report_data["summary"],
                markdown=report_data["markdown"],
                confidence=state.get("confidence", 0.0),
                sources=state.get("sources", []),
                claims=state.get("findings", []),
                contradictions=state.get("contradictions", []),
            )
            db.add(report)
            job.status = "completed"
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
            await cache.append_event(key, {"type": "done", "report_id": report.id, "ts": time.time()})
        except Exception as exc:
            log.exception("research job %s failed", job_id)
            await db.rollback()
            job.status = "failed"
            job.error = str(exc)[:1000]
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
            await cache.append_event(key, {"type": "error", "message": job.error, "ts": time.time()})
