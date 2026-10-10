from collections.abc import Sequence

from langchain_core.tools import BaseTool

from pr_review.infrastructure.config import RepositoryToolConfig
from pr_review.tools.kubernetes import kubectl

TOOL_REGISTRY = {
    "kubectl": kubectl,
}


def resolve_tools(configured_tools: Sequence[RepositoryToolConfig]) -> list[BaseTool]:
    resolved = []
    for configured in configured_tools:
        try:
            resolved.append(TOOL_REGISTRY[configured.name])
        except KeyError as exc:
            raise ValueError(f"unsupported repository tool: {configured.name}") from exc
    return resolved
