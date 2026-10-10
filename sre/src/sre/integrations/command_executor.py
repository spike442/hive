import json
import subprocess
from pathlib import Path

from langchain_core.tools import ToolException

from sre.infrastructure.config import Settings
from sre.integrations.shell import run_shell


class CommandExecutor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.working_directory = Path(settings.repository.path)

    def run(self, command: str, timeout_seconds: int) -> str:
        try:
            result = run_shell(
                command,
                timeout_seconds=timeout_seconds,
                cwd=str(self.working_directory),
                allowed_binaries=self.settings.llm.shell.allowed_binaries,
                denied_patterns=self.settings.llm.shell.denied_patterns,
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolException("command timed out") from exc
        except (OSError, ValueError) as exc:
            raise ToolException(str(exc)) from exc
        return json.dumps(self._redact(result))

    def _redact(self, result: dict) -> dict:
        secrets = (
            self.settings.openai_api_key,
            self.settings.s3.secret_access_key,
            self.settings.s3.access_key_id,
        )
        redacted = dict(result)
        for field in ("command", "stdout", "stderr"):
            value = str(redacted.get(field, ""))
            for secret in secrets:
                if secret:
                    value = value.replace(secret, "[REDACTED]")
            redacted[field] = value
        return redacted
