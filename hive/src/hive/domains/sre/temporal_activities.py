from typing import TYPE_CHECKING

from core.domain import AgentDomain
from core.orchestration import ActivityName
from temporalio import activity

from hive.domains.sre.incident_repository import IncidentRepository
from hive.domains.sre.incident_service import IncidentService
from hive.domains.sre.manual_actions import ManualActionService
from hive.infrastructure.config import Settings

if TYPE_CHECKING:
    from hive.rag.retriever import RagRetriever


class SreTemporalActivities:
    def __init__(
        self,
        incidents: IncidentRepository,
        incident_service: IncidentService,
        manual_actions: ManualActionService,
        settings: Settings,
        rag: RagRetriever | None,
    ):
        self.incidents = incidents
        self.incident_service = incident_service
        self.manual_actions = manual_actions
        self.settings = settings
        self.rag = rag

    def registered(self) -> list:
        return [
            self.queue_replay,
            self.rag_context,
            self.mark_processing,
            self.complete,
            self.fail,
            self.execute_manual_action,
        ]

    @activity.defn(name=ActivityName.SRE_QUEUE_REPLAY.value)
    def queue_replay(self, request: dict) -> bool:
        return self.incidents.queue_replay(request["incident_id"], request["workflow_id"])

    @activity.defn(name=ActivityName.SRE_RAG_CONTEXT.value)
    def rag_context(self, request: dict) -> list[dict]:
        if self.rag is None:
            return []
        incident = request.get("incident") or {"alert": request["alert"]}
        query = self.rag.query_text(incident["alert"])
        if request["kind"] == "replay":
            query = f"{request['prompt']}\n{query}"
        return [
            context.model_dump(mode="json")
            for context in self.rag.retrieve(AgentDomain.SRE.value, self.settings.incident.repository, query)
        ]

    @activity.defn(name=ActivityName.SRE_MARK_PROCESSING.value)
    def mark_processing(self, request: dict) -> bool:
        return self.incidents.mark_processing(
            request["incident_id"],
            request["workflow_id"],
            request.get("prompt", "") if request["kind"] == "replay" else "",
        )

    @activity.defn(name=ActivityName.SRE_COMPLETE.value)
    def complete(self, request: dict) -> None:
        incident = request["incident"]
        incident["workflow_id"] = request["workflow_id"]
        if not self.incidents.is_current(incident["id"], request["workflow_id"]):
            return
        self.incidents.save(self.incident_service.apply(incident))

    @activity.defn(name=ActivityName.SRE_FAIL.value)
    def fail(self, request: dict) -> None:
        self.incidents.mark_failed(request["incident_id"], request["workflow_id"], request["error"])

    @activity.defn(name=ActivityName.MANUAL_ACTION.value)
    def execute_manual_action(self, request: dict) -> dict:
        return self.manual_actions.execute(request["incident_id"], request["action_index"])
