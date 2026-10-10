import asyncio
import logging
import threading

from core.domain import Agent, AgentConfig, AgentDomain, AgentStatus

from hive.application.health import AgentHealth
from hive.integrations.discord import HiveDiscord
from hive.persistence.agent_repository import AgentRepository

logger = logging.getLogger(__name__)


class AgentService:
    """Manage configured agent state and health."""

    def __init__(
        self,
        agents: list[AgentConfig],
        repository: AgentRepository,
        health: AgentHealth,
        discord: HiveDiscord,
    ):
        self.agents = {agent.domain: agent for agent in agents}
        self.repository = repository
        self.health = health
        self.discord = discord
        self._last_status: dict[AgentDomain, AgentStatus] = {}
        self._stopped = threading.Event()
        self.repository.ensure_agents()

    def list_agents(self) -> list[Agent]:
        return [self.status(domain) for domain in self.agents]

    def status(self, domain: AgentDomain) -> Agent:
        config = self.agents[domain]
        healthy, version = self.health.check(config)
        if not healthy:
            status = AgentStatus.DOWN
        elif self.is_active(domain):
            status = AgentStatus.ACTIVE
        else:
            status = AgentStatus.IDLE
        return Agent(domain=config.domain, status=status, healthy=healthy, version=version)

    def check_statuses(self) -> None:
        for domain in self.agents:
            agent = self.status(domain)
            if self._last_status.get(domain) != agent.status:
                self.discord.status(agent)
                self._last_status[domain] = agent.status

    async def run(self) -> None:
        while not self._stopped.is_set():
            try:
                await asyncio.to_thread(self.check_statuses)
            except Exception:
                logger.exception("Agent status monitoring failed")
            await asyncio.to_thread(self._stopped.wait, 5)

    def stop(self) -> None:
        self._stopped.set()

    def set_status(self, domain: AgentDomain, status: AgentStatus) -> Agent:
        if domain not in self.agents:
            raise KeyError(domain)
        self.repository.set_status(domain, status)
        return self.status(domain)

    def is_active(self, domain: AgentDomain) -> bool:
        return self.repository.is_active(domain)

    def close(self) -> None:
        self.discord.close()
