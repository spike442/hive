import logging

import httpx
from core.domain import Agent, AgentStatus

logger = logging.getLogger(__name__)


class HiveDiscord:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.client = httpx.Client(timeout=15)

    def status(self, agent: Agent) -> None:
        titles = {
            AgentStatus.ACTIVE: (f"🟢 {agent.domain.value} is active", 0x2ECC71),
            AgentStatus.IDLE: (f"🟠 {agent.domain.value} is idle", 0xF1C40F),
            AgentStatus.DOWN: (f"🔴 {agent.domain.value} is down", 0xE74C3C),
        }
        title, color = titles[agent.status]
        try:
            response = self.client.post(
                self.webhook_url,
                json={
                    "username": "Hive",
                    "embeds": [
                        {
                            "title": title,
                            "color": color,
                            "fields": [
                                {"name": "Domain", "value": agent.domain.value, "inline": True},
                                {"name": "Version", "value": agent.version or "unknown", "inline": True},
                            ],
                            "footer": {"text": "Hive"},
                        }
                    ],
                },
            )
            if response.is_error:
                raise RuntimeError(f"Discord webhook rejected status={response.status_code}")
        except Exception:
            logger.exception("Hive Discord notification failed agent=%s status=%s", agent.domain.value, agent.status)

    def close(self) -> None:
        self.client.close()
