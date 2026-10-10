from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from pr_review.tools.context import ToolContext


class KubectlArguments(BaseModel):
    args: list[str] = Field(description="kubectl arguments to execute in the configured cluster context.")


@tool(args_schema=KubectlArguments)
def kubectl(args: list[str], runtime: ToolRuntime[ToolContext]) -> str:
    """Run kubectl in the configured cluster context."""

    return runtime.context.executor.run("kubectl", args)
