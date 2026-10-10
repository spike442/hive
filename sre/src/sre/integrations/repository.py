import subprocess
import threading

from sre.infrastructure.config import Settings


class RepositorySync:
    _sync_lock = threading.Lock()

    def __init__(self, settings: Settings):
        self.settings = settings

    def sync_repository(self) -> dict[str, str]:
        """Synchronize the configured public repository to its latest branch head."""
        path = self.settings.repository.path
        branch = self.settings.repository.branch
        remote = self.settings.repository.url
        with self._sync_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            if (path / ".git").is_dir():
                self._git(["-C", str(path), "remote", "set-url", "origin", remote])
                self._git(["-C", str(path), "fetch", "--prune", "origin", branch])
                self._git(["-C", str(path), "checkout", "-B", branch, f"origin/{branch}"])
                self._git(["-C", str(path), "reset", "--hard", f"origin/{branch}"])
            else:
                self._git(["clone", "--single-branch", "--branch", branch, remote, str(path)])
            commit = self._git(["-C", str(path), "rev-parse", "HEAD"]).strip()
        return {"path": str(path), "branch": branch, "commit": commit}

    @staticmethod
    def _git(arguments: list[str]) -> str:
        result = subprocess.run(["git", *arguments], capture_output=True, text=True, timeout=120, check=False)
        if result.returncode:
            raise RuntimeError(f"git operation failed: {result.stderr[-1000:]}")
        return result.stdout
