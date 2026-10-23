import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from ..cache import get_cache
from ..db import SessionLocal, get_db
from ..deps import current_user
from ..models import Report, ResearchJob, User
from ..schemas import JobDetail, JobOut, JobSummary, ReportOut, ResearchCreate
from ..services import events_key, run_job

router = APIRouter(prefix="/api", tags=["research"])
TERMINAL = {"done", "error"}


async def _own_job(job_id: str, user: User, db: AsyncSession) -> ResearchJob:
    job = await db.scalar(
        select(ResearchJob).options(selectinload(ResearchJob.report)).where(ResearchJob.id == job_id)
    )
    if job is None or job.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Research job not found")
    return job


@router.post("/research", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def start_research(
    body: ResearchCreate,
    background: BackgroundTasks,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ResearchJob:
    job = ResearchJob(user_id=user.id, question=body.question.strip())
    db.add(job)
    await db.commit()
    background.add_task(run_job, job.id)
    return job


@router.get("/research", response_model=list[JobSummary])
async def list_research(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> list[JobSummary]:
    jobs = await db.scalars(
        select(ResearchJob)
        .options(selectinload(ResearchJob.report))
        .where(ResearchJob.user_id == user.id)
        .order_by(ResearchJob.created_at.desc())
        .limit(50)
    )
    out = []
    for job in jobs:
        summary = JobSummary.model_validate(job)
        if job.report:
            summary.title = job.report.title
            summary.confidence = job.report.confidence
            summary.contradictions = len(job.report.contradictions)
        out.append(summary)
    return out


@router.get("/research/{job_id}", response_model=JobDetail)
async def get_research(job_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> ResearchJob:
    return await _own_job(job_id, user, db)


@router.delete("/research/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research(job_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> None:
    job = await _own_job(job_id, user, db)
    await db.delete(job)
    await db.commit()
    await get_cache().delete(events_key(job_id))


@router.get("/research/{job_id}/events")
async def stream_events(job_id: str, request: Request, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await _own_job(job_id, user, db)
    cache = get_cache()
    key = events_key(job_id)

    async def generator():
        cursor = 0
        idle = 0
        while not await request.is_disconnected():
            events = await cache.read_events(key, cursor)
            cursor += len(events)
            for event in events:
                yield {"event": event["type"], "data": json.dumps(event)}
                if event["type"] in TERMINAL:
                    return
            idle = 0 if events else idle + 1
            if idle and idle % 10 == 0:
                # Event log may have expired; fall back to the database for the terminal state.
                async with SessionLocal() as s:
                    job = await s.get(ResearchJob, job_id)
                    if job and job.status in ("completed", "failed"):
                        report = await s.scalar(select(Report).where(Report.job_id == job_id))
                        kind = "done" if job.status == "completed" else "error"
                        yield {"event": kind, "data": json.dumps({"type": kind, "report_id": report.id if report else None, "message": job.error})}
                        return
            await asyncio.sleep(0.4)

    return EventSourceResponse(generator(), ping=15)


@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report(report_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)) -> Report:
    report = await db.scalar(select(Report).options(selectinload(Report.job)).where(Report.id == report_id))
    if report is None or report.job.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return report
