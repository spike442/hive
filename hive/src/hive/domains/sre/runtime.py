from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.domain import AgentConfig
from temporalio.client import Client

from hive.domains.sre.application_service import SreApplicationService
from hive.domains.sre.incident_repository import IncidentRepository
from hive.domains.sre.incident_service import IncidentService
from hive.domains.sre.manual_actions import ManualActionService
from hive.domains.sre.temporal_activities import SreTemporalActivities
from hive.infrastructure.config import Settings
from hive.integrations.github import GitHubGateway
from hive.persistence.database import Database

if TYPE_CHECKING:
    from hive.rag.retriever import RagRetriever


@dataclass
class SreRuntime:
    config: AgentConfig
    service: SreApplicationService
    activities: list

    @classmethod
    def load(
        cls,
        config: AgentConfig,
        settings: Settings,
        database: Database,
        github: GitHubGateway,
        temporal: Client,
        rag: RagRetriever | None,
    ) -> "SreRuntime":
        incidents = IncidentRepository(database)
        incident_service = IncidentService(settings, github)
        manual_actions = ManualActionService(settings.execution, incidents)
        service = SreApplicationService(settings, incidents, manual_actions, temporal)
        activities = SreTemporalActivities(incidents, incident_service, manual_actions, settings, rag)
        return cls(config, service, activities.registered())
