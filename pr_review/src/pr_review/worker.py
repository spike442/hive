from core.domain import PullRequest
from core.orchestration import ActivityName
from temporalio import activity

from pr_review.application.exceptions import ReviewExecutionError
from pr_review.application.workflow import ReviewWorkflow
from pr_review.infrastructure.config import RepositoryConfig


class PullRequestReviewActivities:
    def __init__(self, workflow: ReviewWorkflow):
        self.workflow = workflow

    @activity.defn(name=ActivityName.PR_REVIEW.value)
    def review(self, request: dict) -> dict:
        pull_request = PullRequest.model_validate(request["pull_request"])
        repository = RepositoryConfig.model_validate(request["repository"])
        try:
            return self.workflow.process(pull_request, repository, request["rag_context"])
        except ReviewExecutionError as error:
            return {
                "failure": type(error.__cause__).__name__,
                "pull_request": pull_request.model_dump(mode="json"),
                "review_actions": [action.model_dump(mode="json") for action in error.actions],
            }
