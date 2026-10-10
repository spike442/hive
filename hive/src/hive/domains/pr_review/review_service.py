import logging
from datetime import UTC, datetime

from core.domain import ReviewStatus

from hive.domains.pr_review.review_repository import ReviewRepository
from hive.integrations.github import GitHubGateway

logger = logging.getLogger(__name__)


class ReviewService:
    """Persist PR review decisions and apply approved merges in Hive."""

    def __init__(self, reviews: ReviewRepository, github: GitHubGateway, merge_method: str):
        self.reviews = reviews
        self.github = github
        self.merge_method = merge_method

    def complete(self, result: dict, workflow_id: str) -> None:
        review = result.get("review") or result
        pull_request = review.get("pull_request") or result.get("pull_request") or {}
        if pull_request and self.reviews.is_merged(pull_request):
            logger.info(
                "Ignoring duplicate completed review repository=%s number=%s",
                pull_request.get("repository"),
                pull_request.get("number"),
            )
            return
        self.reviews.save(result, workflow_id)
        decision = review.get("decision") or {}
        if not pull_request or not decision.get("merge"):
            return

        try:
            merged_sha = self.github.merged_commit(pull_request)
            if merged_sha:
                self.reviews.mark_merged(pull_request, workflow_id, merged_sha, datetime.now(UTC))
                return
            if not self.github.is_mergeable(pull_request):
                self.reviews.update_status(
                    pull_request,
                    ReviewStatus.PENDING.value,
                    "GitHub is no longer mergeable or clean after review.",
                    workflow_id=workflow_id,
                )
                return
            merge_sha = self.github.merge_pull_request(pull_request, self.merge_method)
        except Exception as exc:
            self.reviews.update_status(
                pull_request,
                ReviewStatus.FAILED.value,
                f"GitHub merge failed: {type(exc).__name__}.",
                workflow_id=workflow_id,
            )
            logger.exception(
                "GitHub merge failed repository=%s number=%s",
                pull_request.get("repository"),
                pull_request.get("number"),
            )
            return

        self.reviews.mark_merged(pull_request, workflow_id, merge_sha, datetime.now(UTC))
        logger.info(
            "Pull request merged repository=%s number=%s sha=%s",
            pull_request.get("repository"),
            pull_request.get("number"),
            merge_sha,
        )
