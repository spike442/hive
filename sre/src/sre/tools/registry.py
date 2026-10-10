from langchain_core.tools import BaseTool

from sre.infrastructure.config import ToolConfig
from sre.tools.prometheus import query_metrics
from sre.tools.shell import run_shell

TOOL_REGISTRY: dict[str, BaseTool] = {
    "run_shell": run_shell,
    "query_prometheus": query_metrics,
}


def resolve_tools(configured_tools: list[ToolConfig]) -> list[BaseTool]:
    try:
        return [TOOL_REGISTRY[tool.name] for tool in configured_tools]
    except KeyError as exc:
        raise ValueError(f"unsupported SRE tool: {exc.args[0]}") from exc
