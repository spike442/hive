import logging
from dataclasses import dataclass
from typing import Protocol

from core.domain import ConfidenceLevel, RetrievedContext, RiskLevel
from core.observability.audit import AuditLog
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI

from pr_review.domain.review import PullRequest, ReviewResult
from pr_review.infrastructure.config import RepositoryToolConfig
from pr_review.integrations.audit_middleware import ReviewAuditMiddleware
from pr_review.integrations.command_executor import CommandExecutor
from pr_review.tools import ToolContext, resolve_tools

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReviewRequest:
    """Typed input bundle for one isolated pull-request review."""

    pull_request: PullRequest
    diff: str
    system_prompt: str
    prompt_version: str
    action_prompt: str
    tools: tuple[RepositoryToolConfig, ...]
    audit: AuditLog
    rag_context: list[RetrievedContext]


class ReviewEngine(Protocol):
    def review(self, request: ReviewRequest) -> ReviewResult: ...


class LangChainReviewEngine:
    def __init__(self, settings, command_executor: CommandExecutor):
        self.model = ChatOpenAI(
            model=settings.llm.model,
            api_key=settings.openai_api_key,
            base_url=settings.llm.base_url,
            max_retries=settings.llm.max_retries,
            use_responses_api=True,
            output_version="responses/v1",
        )
        self.prompt_cache_key = settings.llm.prompt_cache_key
        self.max_tool_calls = settings.review.max_tool_calls
        self.command_executor = command_executor

    def review(self, request: ReviewRequest) -> ReviewResult:
        try:
            pull_request = request.pull_request
            cache_key = f"{self.prompt_cache_key}:{pull_request.repository}:{request.prompt_version}"
            agent = create_agent(
                model=self.model.bind(prompt_cache_key=cache_key),
                tools=resolve_tools(request.tools),
                context_schema=ToolContext,
                system_prompt=f"{request.action_prompt}\n\nReviewer instructions:\n{request.system_prompt}",
                response_format=ToolStrategy(ReviewResult),
                middleware=[
                    ToolCallLimitMiddleware(run_limit=self.max_tool_calls, exit_behavior="error"),
                    ReviewAuditMiddleware(),
                ],
            )
            result = agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": self._review_request(pull_request, request.diff, request.rag_context),
                        }
                    ]
                },
                config={
                    "run_name": f"pr-review-{pull_request.repository}-{pull_request.number}",
                    "tags": ["pr-review", pull_request.repository],
                    "metadata": {
                        "repository": pull_request.repository,
                        "pull_request": pull_request.number,
                        "head_sha": pull_request.head_sha,
                    },
                },
                context=ToolContext(executor=self.command_executor, audit=request.audit),
            )
            review = result.get("structured_response")
            if not isinstance(review, ReviewResult):
                raise ValueError("LangChain did not return a structured review")
            request.audit.record("review_submitted", review.model_dump(mode="json"))
            logger.info(
                "review completed repository=%s number=%s risk=%s confidence=%s",
                pull_request.repository,
                pull_request.number,
                review.risk,
                review.confidence,
            )
            return review
        except Exception as exc:
            logger.warning(
                "LLM review failed repository=%s number=%s error=%s",
                pull_request.repository,
                pull_request.number,
                type(exc).__name__,
            )
            return ReviewResult(
                risk=RiskLevel.HIGH,
                confidence=ConfidenceLevel.LOW,
                summary="The review could not be completed; merge is blocked.",
                findings=["LLM review failed before a valid decision was returned."],
            )

    @staticmethod
    def _review_request(pull_request: PullRequest, diff: str, rag_context: list[RetrievedContext]) -> str:
        content = (
            f"Review pull request #{pull_request.number} in "
            f"{pull_request.owner}/{pull_request.repository}.\n\n"
            f"Title: {pull_request.title}\n"
            f"Author: {pull_request.author}\n"
            f"Head branch: {pull_request.head_ref}\n"
            f"Labels: {', '.join(pull_request.labels)}\n"
            f"Head SHA: {pull_request.head_sha}\n\n"
            f"Diff:\n{diff}"
        )
        if rag_context:
            content += "\n\nRetrieved reference material (verify against the current repository and live state):\n"
            content += "\n\n".join(f"Source: {item.source}\n{item.content}" for item in rag_context)
        return content

    def close(self) -> None:
        self.model.root_client.close()
