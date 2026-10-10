import httpx
from core.domain import AgentConfig

HEALTH_PATH = "/healthz"


class AgentHealth:
    def __init__(self, timeout_seconds: float):
        self.client = httpx.Client(timeout=timeout_seconds)

    def check(self, agent: AgentConfig) -> tuple[bool, str]:
        try:
            health = self.client.get(f"{agent.base_url.rstrip('/')}{HEALTH_PATH}")
            if not health.is_success:
                return False, ""
            data = health.json()
            return data.get("status") == "ok", str(data.get("version", ""))
        except (httpx.HTTPError, ValueError):
            return False, ""

    def close(self) -> None:
        self.client.close()
