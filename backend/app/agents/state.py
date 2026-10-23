from typing import Literal, TypedDict

from pydantic import BaseModel, Field

ClaimStatus = Literal["corroborated", "single-source", "contested"]


class Claim(BaseModel):
    id: int
    text: str
    source: int  # 1-based index into ResearchState.sources


class Finding(BaseModel):
    statement: str
    sources: list[int] = Field(default_factory=list)
    status: ClaimStatus = "single-source"


class Contradiction(BaseModel):
    topic: str
    claim_a: str
    source_a: int
    claim_b: str
    source_b: int
    explanation: str
    likely_correct: Literal["a", "b", "unclear"] = "unclear"


class ResearchState(TypedDict, total=False):
    question: str
    sub_queries: list[str]
    round: int
    sources: list[dict]
    claims: list[dict]
    findings: list[dict]
    contradictions: list[dict]
    confidence: float
    report: dict
