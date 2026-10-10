from datetime import datetime

from core.domain import ConfidenceLevel, PullRequest, ReviewStatus, RiskLevel
from core.observability.audit import AuditAction
from pydantic import BaseModel, Field


class CheckResult(BaseModel):
    name: str
    passed: bool
    output: str = ""


class ReviewResult(BaseModel):
    risk: RiskLevel
    confidence: ConfidenceLevel
    summary: str
    findings: list[str] = Field(default_factory=list)


class ReviewDecision(BaseModel):
    merge: bool
    reason: str


class ReviewAssessment(BaseModel):
    pull_request: PullRequest
    checks: list[CheckResult]
    review: ReviewResult
    review_actions: list[AuditAction] = Field(default_factory=list)


class PullRequestReview(BaseModel):
    pull_request: PullRequest
    checks: list[CheckResult]
    review: ReviewResult
    mergeable: bool
    decision: ReviewDecision
    review_actions: list[AuditAction] = Field(default_factory=list)
    merged_at: datetime | None = None
    merge_commit_sha: str = ""
    status: ReviewStatus = ReviewStatus.DECIDED
