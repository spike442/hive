import json
import subprocess

from langchain_core.tools import ToolException

from pr_review.infrastructure.config import ReviewConfig


class CommandExecutor:
    def __init__(self, config: ReviewConfig):
        self.timeout_seconds = config.command_timeout_seconds
        self.max_output_bytes = config.max_tool_output_bytes
        self.working_directory = config.workspace_root

    def run(self, command: str, args: list[str]) -> str:
        try:
            result = subprocess.run(
                [command, *args],
                cwd=self.working_directory,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolException(f"{command} timed out") from exc
        except OSError as exc:
            raise ToolException(f"{command} could not run: {type(exc).__name__}") from exc
        return json.dumps({"exit_code": result.returncode, "output": result.stdout[: self.max_output_bytes]})
