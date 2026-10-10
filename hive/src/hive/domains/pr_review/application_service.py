from __future__ import annotations

import asyncio
from uuid import uuid4

from core.domain import AgentDomain, ReviewStatus
from core.orchestration import WorkflowType
from temporalio.client import Client

from hive.domains.pr_review.review_repository import ReviewRepository
from hive.infrastructure.config import Settings
from hive.integrations.github import GitHubGateway
from hive.rag.retriever import RagRetriever


class PrReviewApplicationService:
    """Start pull-request workflows and expose persisted reviews to Hive's API."""

    def __init__(
        self,
        settings: Settings,
        reviews: ReviewRepository,
        rag: RagRetriever | None,
        github: GitHubGateway,
        temporal: Client,
    ):
        self.settings = settings
        self.reviews = reviews
        self.rag = rag
        self.github = github
        self.temporal = temporal
        self.repositories = {(repo.owner, repo.name): repo for repo in settings.repositories}

    async def check_now(self) -> str:
        workflow_id = f"pr-review-poll-{uuid4()}"
        await self.temporal.start_workflow(
            WorkflowType.PR_REVIEW_POLL.value,
            id=workflow_id,
            task_queue=self.settings.temporal.workflow_task_queue,
            static_summary="Manually triggered PR review scan",
        )
        return workflow_id

    async def retry(self, review_id: int) -> str:
        review = await asyncio.to_thread(self.reviews.get, review_id)
        if review["status"] != ReviewStatus.FAILED.value:
            raise ValueError("Only failed reviews can be retried")
        repository = self.repositories[(review["owner"], review["repository"])]
        pull_request = await asyncio.to_thread(self.github.pull_request, repository, review["pull_request_number"])
        if pull_request["head_sha"] != review["head_sha"]:
            raise ValueError("The PR changed; use Check now to review its latest revision")
        workflow_id = f"pr-review-retry-{uuid4()}"
        await self.temporal.start_workflow(
            WorkflowType.PR_REVIEW.value,
            self.review_request(pull_request),
            id=workflow_id,
            task_queue=self.settings.temporal.workflow_task_queue,
            static_summary=f"PR review {review['owner']}/{review['repository']}#{review['pull_request_number']}",
        )
        return workflow_id

    def discover(self) -> list[dict]:
        return [
            self.review_request(pull_request)
            for repository in self.settings.repositories
            for pull_request in self.github.open_pull_requests(repository)
            if self.reviews.needs_review(pull_request)
        ]

    def review_request(self, pull_request: dict) -> dict:
        repository = pull_request.get("repository_config")
        if repository is None:
            repository = self.repositories[(pull_request["owner"], pull_request["repository"])].model_dump(mode="json")
        request_pull = {key: value for key, value in pull_request.items() if key != "repository_config"}
        return {
            "pull_request": request_pull,
            "repository": repository,
            "agent_task_queue": self.settings.temporal.pr_review_task_queue,
        }

    def prepare_review(self, request: dict) -> dict:
        pull_request = request["pull_request"]
        rag_context = (
            [
                context.model_dump(mode="json")
                for context in self.rag.retrieve(
                    AgentDomain.PULL_REQUEST_REVIEW.value,
                    pull_request["repository"],
                    self.rag.query_text(pull_request),
                )
            ]
            if self.rag is not None
            else []
        )
        return {**request, "rag_context": rag_context}

    def list_reviews(self, limit: int, status: str | None) -> list[dict]:
        return self.reviews.list(limit, status)

    def delete(self, review_id: int) -> None:
        self.reviews.delete(review_id)
