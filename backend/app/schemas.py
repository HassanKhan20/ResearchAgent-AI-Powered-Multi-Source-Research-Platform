from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    created_at: datetime


class SessionOut(BaseModel):
    token: str
    user: UserOut


class ResearchCreate(BaseModel):
    question: str = Field(min_length=8, max_length=500)


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    title: str
    summary: str
    markdown: str
    confidence: float
    sources: list[dict]
    claims: list[dict]
    contradictions: list[dict]
    created_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    question: str
    status: str
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class JobSummary(JobOut):
    title: str | None = None
    confidence: float | None = None
    contradictions: int = 0


class JobDetail(JobOut):
    report: ReportOut | None = None
