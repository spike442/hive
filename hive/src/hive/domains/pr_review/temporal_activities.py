from core.orchestration import ActivityName
from temporalio import activity

from hive.domains.pr_review.application_service import PrReviewApplicationService
from hive.domains.pr_review.review_repository import ReviewRepository
from hive.domains.pr_review.review_service import ReviewService


class PrReviewTemporalActivities:
    def __init__(
        self,
        reviews: ReviewRepository,
        review_service: ReviewService,
        application: PrReviewApplicationService,
    ):
        self.reviews = reviews
        self.review_service = review_service
        self.application = application

    def registered(self) -> list:
        return [self.discover, self.acknowledge, self.claim, self.prepare, self.complete, self.fail]

    @activity.defn(name=ActivityName.PR_DISCOVER.value)
    def discover(self) -> list[dict]:
        return self.application.discover()

    @activity.defn(name=ActivityName.PR_ACKNOWLEDGE.value)
    def acknowledge(self, request: dict) -> None:
        self.reviews.acknowledge(request["pull_request"])

    @activity.defn(name=ActivityName.PR_CLAIM.value)
    def claim(self, request: dict) -> bool:
        return self.reviews.claim(request["pull_request"], request["workflow_id"])

    @activity.defn(name=ActivityName.PR_PREPARE.value)
    def prepare(self, request: dict) -> dict:
        return self.application.prepare_review(request)

    @activity.defn(name=ActivityName.PR_COMPLETE.value)
    def complete(self, request: dict) -> None:
        self.review_service.complete(request["review"], request["workflow_id"])

    @activity.defn(name=ActivityName.PR_FAIL.value)
    def fail(self, request: dict) -> None:
        self.reviews.fail(request)
