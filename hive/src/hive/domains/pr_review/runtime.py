from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.domain import AgentConfig
from temporalio.client import Client

from hive.domains.pr_review.application_service import PrReviewApplicationService
from hive.domains.pr_review.review_repository import ReviewRepository
from hive.domains.pr_review.review_service import ReviewService
from hive.domains.pr_review.temporal_activities import PrReviewTemporalActivities
from hive.infrastructure.config import Settings
from hive.integrations.github import GitHubGateway
from hive.persistence.database import Database

if TYPE_CHECKING:
    from hive.rag.retriever import RagRetriever


@dataclass
class PrReviewRuntime:
    config: AgentConfig
    service: PrReviewApplicationService
    activities: list

    @classmethod
    def load(
        cls,
        config: AgentConfig,
        settings: Settings,
        database: Database,
        github: GitHubGateway,
        temporal: Client,
        rag: RagRetriever | None,
    ) -> "PrReviewRuntime":
        if config.job_interval_seconds is None:
            raise ValueError(f"job_interval_seconds is required for domain: {config.domain.value}")

        reviews = ReviewRepository(database)
        review_service = ReviewService(reviews, github, settings.github.merge_method)
        service = PrReviewApplicationService(settings, reviews, rag, github, temporal)
        activities = PrReviewTemporalActivities(reviews, review_service, service)
        return cls(config, service, activities.registered())
