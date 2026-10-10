from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from sre.tools.context import ToolContext


class ShellArguments(BaseModel):
    command: str = Field(description="One bounded read-only Linux diagnostic command or pipeline.")
    timeout_seconds: int = Field(default=20, description="Command timeout in seconds.")


@tool(args_schema=ShellArguments)
def run_shell(command: str, timeout_seconds: int, runtime: ToolRuntime[ToolContext]) -> str:
    """Run a bounded read-only diagnostic command in the repository and cluster environment."""

    return runtime.context.executor.run(command, timeout_seconds)
