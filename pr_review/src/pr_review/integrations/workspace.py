import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

from core.observability.audit import AuditLog

from pr_review.domain.review import CheckResult, PullRequest
from pr_review.infrastructure.config import RepositoryConfig


def _record_command(
    audit: AuditLog,
    command: list[str],
    exit_code: int | None,
    output: str,
) -> None:
    audit.record("workspace_command", {"command": command, "exit_code": exit_code, "output": output})


class WorkspaceManager:
    """Clone and validate untrusted PR code in a disposable workspace."""

    def __init__(self, root: Path, timeout_seconds: int):
        self.root = root
        self.timeout_seconds = timeout_seconds

    @contextmanager
    def checkout(self, pull_request: PullRequest, repository: RepositoryConfig, audit: AuditLog):
        self.root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f"pr-{pull_request.number}-", dir=self.root) as temporary_directory:
            workspace = Path(temporary_directory)
            self._run(
                [
                    "git",
                    "clone",
                    "--depth",
                    str(repository.clone_depth),
                    "--no-checkout",
                    repository.clone_url,
                    str(workspace),
                ],
                self.root,
                audit,
            )
            self._run(["git", "fetch", "origin", f"pull/{pull_request.number}/head"], workspace, audit)
            self._run(["git", "fetch", "origin", pull_request.base_sha], workspace, audit)
            self._run(["git", "checkout", "--detach", pull_request.head_sha], workspace, audit)
            yield workspace

    def run_checks(self, checkout: Path, pull_request: PullRequest, audit: AuditLog) -> list[CheckResult]:
        result = self._run(
            ["git", "diff", "--check", pull_request.base_sha, pull_request.head_sha], checkout, audit, check=False
        )
        return [CheckResult(name="git diff --check", passed=result.returncode == 0, output=result.stdout)]

    def diff(self, checkout: Path, pull_request: PullRequest, audit: AuditLog, max_bytes: int) -> str:
        result = self._run(
            ["git", "diff", "--no-ext-diff", "--unified=80", pull_request.base_sha, pull_request.head_sha],
            checkout,
            audit,
        )
        return result.stdout[:max_bytes]

    def _run(
        self,
        command: list[str],
        cwd: Path,
        audit: AuditLog,
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                check=check,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=self.timeout_seconds,
            )
        except subprocess.CalledProcessError as exc:
            _record_command(audit, command, exc.returncode, exc.output or "")
            raise
        except subprocess.TimeoutExpired as exc:
            _record_command(audit, command, None, str(exc.output or ""))
            raise
        except OSError as exc:
            _record_command(audit, command, None, type(exc).__name__)
            raise
        _record_command(audit, command, result.returncode, result.stdout)
        return result
