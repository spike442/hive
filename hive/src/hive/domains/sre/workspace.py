import hashlib
import json
import subprocess
import threading

from hive.infrastructure.config import IncidentConfig, RepositoryConfig


class IncidentWorkspace:
    """Prepare SRE's target repository and publish an incident fix branch."""

    _git_lock = threading.Lock()

    def __init__(self, repository: RepositoryConfig, incident: IncidentConfig):
        self.repository = repository
        self.incident = incident

    def branch_for(self, changes: list[dict]) -> str:
        identity = json.dumps(sorted(changes, key=lambda change: change["file_path"]), sort_keys=True).encode()
        digest = hashlib.sha256(identity).hexdigest()[:16]
        return f"{self.incident.branch_prefix}/{self.incident.version}/{digest}"

    def push_changes(self, changes: list[dict]) -> str:
        with self._git_lock:
            self._sync_repository()
            return self._push_changes(changes)

    def _sync_repository(self) -> None:
        path = self.incident.path
        path.parent.mkdir(parents=True, exist_ok=True)
        if (path / ".git").is_dir():
            self._git(["-C", str(path), "remote", "set-url", "origin", self.repository.clone_url])
            self._git(["-C", str(path), "fetch", "--prune", "origin", self.incident.branch])
            self._git(
                [
                    "-C",
                    str(path),
                    "checkout",
                    "-B",
                    self.incident.branch,
                    f"origin/{self.incident.branch}",
                ]
            )
            self._git(["-C", str(path), "reset", "--hard", f"origin/{self.incident.branch}"])
            return
        self._git(
            [
                "clone",
                "--single-branch",
                "--branch",
                self.incident.branch,
                self.repository.clone_url,
                str(path),
            ]
        )

    def _push_changes(self, changes: list[dict]) -> str:
        path = self.incident.path
        branch = self.branch_for(changes)
        self._git(
            [
                "-C",
                str(path),
                "remote",
                "set-url",
                "origin",
                f"git@github-bot:{self.repository.owner}/{self.repository.name}.git",
            ]
        )
        if self._git(["-C", str(path), "ls-remote", "--heads", "origin", f"refs/heads/{branch}"]).strip():
            return branch
        self._git(["-C", str(path), "checkout", "-B", branch, self.incident.branch])
        for change in changes:
            target = (path / change["file_path"]).resolve()
            if path.resolve() not in target.parents:
                raise ValueError(f"change path escapes repository: {change['file_path']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(change["content"], encoding="utf-8")
        self._git(["-C", str(path), "add", "--", *(change["file_path"] for change in changes)])
        self._git(["-C", str(path), "diff", "--cached", "--check"])
        self._git(["-C", str(path), "config", "user.name", self.incident.commit_author_name])
        self._git(["-C", str(path), "config", "user.email", self.incident.commit_author_email])
        self._git(["-C", str(path), "commit", "-m", changes[0]["title"]])
        self._git(["-C", str(path), "push", "--set-upstream", "origin", branch])
        return branch

    @staticmethod
    def _git(arguments: list[str]) -> str:
        result = subprocess.run(["git", *arguments], capture_output=True, text=True, timeout=120, check=False)
        if result.returncode:
            raise RuntimeError(f"git operation failed: {result.stderr[-1000:]}")
        return result.stdout
