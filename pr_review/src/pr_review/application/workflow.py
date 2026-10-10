import logging
from typing import Any

from core.domain import RetrievedContext
from core.observability.audit import AuditLog

from pr_review.application.exceptions import ReviewExecutionError
from pr_review.application.policy import MergePolicy, decide_merge
from pr_review.domain.review import (
    PullRequest,
    PullRequestReview,
    ReviewAssessment,
    ReviewStatus,
)
from pr_review.infrastructure.config import RepositoryConfig, Settings
from pr_review.integrations.llm_review import ReviewEngine, ReviewRequest

logger = logging.getLogger(__name__)


class ReviewWorkflow:
    """Run one pull-request review and return its decision to Hive."""

    def __init__(
        self,
        settings: Settings,
        workspace,
        engine: ReviewEngine,
        prompt_store,
    ):
        self.settings = settings
        self.workspace = workspace
        self.engine = engine
        self.prompt_store = prompt_store

    def process(
        self,
        pull_request: PullRequest,
        repository: RepositoryConfig,
        rag_context: list[RetrievedContext],
    ) -> dict[str, Any]:
        if not pull_request.mergeable:
            return {
                "status": ReviewStatus.PENDING.value,
                "reason": "Waiting for Hive to confirm GitHub mergeable=true and mergeable_state=clean.",
                "pull_request": pull_request.model_dump(mode="json"),
            }
        assessment = self.review(pull_request, repository, rag_context)
        decision = decide_merge(
            assessment.review,
            MergePolicy(
                checks_passed=all(check.passed for check in assessment.checks),
                mergeable=pull_request.mergeable,
                merge_enabled=self.settings.review.merge_enabled,
                allowed_risk_levels=frozenset(self.settings.review.allowed_risk_levels),
                allowed_confidence_levels=frozenset(self.settings.review.allowed_confidence_levels),
            ),
        )

        review = PullRequestReview(
            pull_request=assessment.pull_request,
            checks=assessment.checks,
            review=assessment.review,
            mergeable=pull_request.mergeable,
            decision=decision,
            review_actions=assessment.review_actions,
        )

        logger.info(
            "PR review completed repository=%s number=%s risk=%s confidence=%s merge=%s",
            repository.name,
            review.pull_request.number,
            review.review.risk,
            review.review.confidence,
            review.decision.merge,
        )
        return review.model_dump(mode="json")

    def review(
        self,
        pull_request: PullRequest,
        repository: RepositoryConfig,
        rag_context: list[RetrievedContext],
    ) -> ReviewAssessment:
        audit = AuditLog()
        try:
            with self.workspace.checkout(pull_request, repository, audit) as checkout:
                checks = self.workspace.run_checks(checkout, pull_request, audit)
                diff = self.workspace.diff(checkout, pull_request, audit, self.settings.review.max_diff_bytes)
                system_key = self.settings.s3.system_key
                action_key = "/".join(
                    part.strip("/")
                    for part in (repository.name, self.settings.s3.action_prompt_prefix, "review.md")
                    if part
                )
                system_prompt = self.prompt_store.text(system_key)
                action_prompt = self.prompt_store.text(action_key)
                review = self.engine.review(
                    ReviewRequest(
                        pull_request=pull_request,
                        diff=diff,
                        system_prompt=system_prompt,
                        prompt_version=self.prompt_store.version([system_key, action_key]),
                        action_prompt=action_prompt,
                        tools=tuple(repository.tools),
                        audit=audit,
                        rag_context=rag_context,
                    )
                )
        except Exception as exc:
            raise ReviewExecutionError(exc, audit.actions) from exc
        return ReviewAssessment(
            pull_request=pull_request,
            checks=checks,
            review=review,
            review_actions=audit.actions,
        )
