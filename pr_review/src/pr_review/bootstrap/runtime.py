from dataclasses import dataclass

from core.integrations.prompts import PromptStore, PromptStoreConfig

from pr_review.application.workflow import ReviewWorkflow
from pr_review.infrastructure.config import Settings
from pr_review.integrations.command_executor import CommandExecutor
from pr_review.integrations.llm_review import LangChainReviewEngine
from pr_review.integrations.workspace import WorkspaceManager


@dataclass
class Runtime:
    """Already-built PR Review resources shared for the process lifetime."""

    workflow: ReviewWorkflow


def build_runtime(settings: Settings) -> Runtime:
    prompt_store = PromptStore(
        PromptStoreConfig(
            bucket=settings.s3.bucket,
            prefix=settings.s3.prefix,
            endpoint=settings.s3.endpoint_url,
            region=settings.s3.region,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            reload_on_change=True,
            max_bytes=settings.s3.max_bytes,
        )
    )
    workspace = WorkspaceManager(settings.review.workspace_root, settings.review.command_timeout_seconds)
    command_executor = CommandExecutor(settings.review)
    workflow = ReviewWorkflow(
        settings,
        workspace,
        LangChainReviewEngine(settings, command_executor),
        prompt_store,
    )
    return Runtime(workflow=workflow)
