from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.domain import AgentDomain
from temporalio.client import Client
from temporalio.worker import Worker

from hive.application.agent_service import AgentService
from hive.application.health import AgentHealth
from hive.domains import DomainRuntime, agents
from hive.domains.sre.messaging import AlertIngress
from hive.infrastructure.config import Settings
from hive.integrations.discord import HiveDiscord
from hive.integrations.github import GitHubGateway
from hive.orchestration.worker import build_worker
from hive.persistence.agent_repository import AgentRepository
from hive.persistence.database import Database

if TYPE_CHECKING:
    from hive.rag.retriever import RagRetriever


@dataclass
class Runtime:
    settings: Settings
    database: Database
    health: AgentHealth
    github: GitHubGateway
    agent_service: AgentService
    agents: dict[AgentDomain, DomainRuntime]
    rag: RagRetriever | None
    temporal_worker: Worker
    activity_executor: ThreadPoolExecutor
    alert_ingress: AlertIngress | None


def build_runtime(settings: Settings, temporal: Client, event_loop) -> Runtime:
    database = Database(settings.database_dsn)
    agents_repository = AgentRepository(database, [agent.domain for agent in settings.agents])
    rag = None
    if settings.rag.enabled:
        from hive.rag.retriever import RagRetriever

        rag = RagRetriever(settings, database)

    health = AgentHealth(settings.health.timeout_seconds)
    github = GitHubGateway(settings)
    agent_service = AgentService(
        settings.agents,
        agents_repository,
        health,
        HiveDiscord(settings.discord_webhook_url),
    )
    runtimes = agents(settings, database, github, rag, temporal)
    activity_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="hive-activity")
    temporal_worker = build_worker(
        temporal,
        settings.temporal.workflow_task_queue,
        agent_service,
        runtimes,
        activity_executor,
    )
    sre = runtimes.get(AgentDomain.SRE)
    alert_ingress = AlertIngress(settings, sre.service, event_loop) if sre is not None else None
    return Runtime(
        settings=settings,
        database=database,
        health=health,
        github=github,
        agent_service=agent_service,
        agents=runtimes,
        rag=rag,
        temporal_worker=temporal_worker,
        activity_executor=activity_executor,
        alert_ingress=alert_ingress,
    )
