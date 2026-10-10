import os
import re
import shlex
import subprocess
from typing import Any


def _validate_command(command: str, allowed_binaries: list[str], denied_patterns: list[str]) -> None:
    if not command or len(command) > 2000:
        raise ValueError("command must be between 1 and 2000 characters")
    for segment in command.split("|"):
        try:
            arguments = shlex.split(segment)
        except ValueError as exc:
            raise ValueError("invalid shell syntax") from exc
        if not arguments or arguments[0] not in set(allowed_binaries):
            raise ValueError(f"command must use approved read-only binaries: {sorted(allowed_binaries)}")
    safety_patterns = (
        r"\b(?:exec|system|eval|source)\b",
        r"(?:;|&&|\|\||>|<|`|\$\(|\n)",
    )
    patterns = [*denied_patterns, *safety_patterns]
    denied = re.compile("|".join(f"(?:{pattern})" for pattern in patterns))
    if denied.search(command):
        raise ValueError("mutating, network, process, or shell-control command is not allowed")


def _execute(command: str, timeout_seconds: int, cwd: str | None) -> dict[str, Any]:
    environment = {
        name: os.environ[name]
        for name in ("PATH", "HOME", "TERM", "KUBECONFIG", "GIT_TERMINAL_PROMPT")
        if name in os.environ
    }
    processes: list[subprocess.Popen] = []
    previous_stdout = None
    try:
        for segment in command.split("|"):
            process = subprocess.Popen(
                shlex.split(segment),
                stdin=previous_stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                env=environment,
            )
            processes.append(process)
            if previous_stdout is not None:
                previous_stdout.close()
            previous_stdout = process.stdout
        stdout, stderr = processes[-1].communicate(timeout=timeout_seconds)
        for process in processes[:-1]:
            process.wait(timeout=timeout_seconds)
        exit_code = processes[-1].returncode
    except subprocess.TimeoutExpired:
        for process in processes:
            process.kill()
        raise
    return {
        "command": command,
        "exit_code": exit_code,
        "stdout": stdout[-12000:],
        "stderr": stderr[-4000:],
    }


def run_shell(
    command: str,
    timeout_seconds: int = 20,
    cwd: str | None = None,
    allowed_binaries: list[str] | None = None,
    denied_patterns: list[str] | None = None,
) -> dict[str, Any]:
    """Execute one bounded, read-only diagnostic shell pipeline."""
    _validate_command(command, allowed_binaries or [], denied_patterns or [])
    return _execute(command, max(1, min(timeout_seconds, 30)), cwd)
