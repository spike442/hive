from __future__ import annotations

import asyncio
from uuid import uuid4

from core.domain import AlertStatus, IncidentStatus
from core.orchestration import WorkflowType
from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from hive.domains.sre.event_handler import alertmanager_alerts
from hive.domains.sre.incident_repository import IncidentRepository
from hive.domains.sre.manual_actions import ManualActionService
from hive.infrastructure.config import Settings


class SreApplicationService:
    """Start durable SRE work and expose persisted incident operations to Hive."""

    def __init__(
        self,
        settings: Settings,
        incidents: IncidentRepository,
        actions: ManualActionService,
        temporal: Client,
    ):
        self.settings = settings
        self.incidents = incidents
        self.actions = actions
        self.temporal = temporal

    async def receive_alert_event(self, event: dict) -> None:
        for alert in alertmanager_alerts(event):
            if not alert["fingerprint"]:
                raise ValueError("Alertmanager event is missing its fingerprint")
            await self._start_alert(alert)

    async def _start_alert(self, alert: dict) -> None:
        incident_id = alert["fingerprint"]
        if alert["status"] == AlertStatus.RESOLVED.value:
            await asyncio.to_thread(self.incidents.resolve, incident_id, alert)
            return

        proposed_id = f"sre-{uuid4()}"
        workflow_id = await asyncio.to_thread(self.incidents.queue, incident_id, alert, proposed_id)
        if workflow_id is None:
            return
        request = {
            "kind": "alert",
            "incident_id": incident_id,
            "alert": alert,
            "agent_task_queue": self.settings.temporal.sre_task_queue,
        }
        try:
            await self.temporal.start_workflow(
                WorkflowType.SRE_INCIDENT.value,
                request,
                id=workflow_id,
                task_queue=self.settings.temporal.workflow_task_queue,
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary=f"SRE incident {incident_id}",
            )
        except WorkflowAlreadyStartedError:
            return

    async def replay(self, incident_id: str, prompt: str) -> str:
        incident = await asyncio.to_thread(self.incidents.get, incident_id)
        if incident is None:
            raise LookupError(f"incident not found: {incident_id}")
        if incident["status"] not in {
            IncidentStatus.ACKNOWLEDGED.value,
            IncidentStatus.FAILED.value,
            IncidentStatus.BLOCKED.value,
        }:
            raise ValueError(f"incident cannot be replayed from {incident['status']}")

        workflow_id = f"sre-replay-{uuid4()}"
        request = {
            "kind": "replay",
            "incident_id": incident_id,
            "incident": incident,
            "prompt": prompt,
            "agent_task_queue": self.settings.temporal.sre_task_queue,
        }
        await self.temporal.start_workflow(
            WorkflowType.SRE_INCIDENT.value,
            request,
            id=workflow_id,
            task_queue=self.settings.temporal.workflow_task_queue,
            static_summary=f"SRE replay {incident_id}",
        )
        return workflow_id

    async def execute_manual_action(self, incident_id: str, action_index: int) -> str:
        incident = await asyncio.to_thread(self.incidents.get, incident_id)
        if incident is None:
            raise LookupError(f"incident not found: {incident_id}")
        workflow_id = f"manual-action-{uuid4()}"
        await self.temporal.start_workflow(
            WorkflowType.MANUAL_ACTION.value,
            {"incident_id": incident_id, "action_index": action_index},
            id=workflow_id,
            task_queue=self.settings.temporal.workflow_task_queue,
            static_summary=f"Approved action for incident {incident_id}",
        )
        return workflow_id

    def list_incidents(self, limit: int, source: str | None, status: str | None) -> list[dict]:
        return self.incidents.list(limit, source, status)

    def get_incident(self, incident_id: str) -> dict | None:
        return self.incidents.get(incident_id)

    def ignore(self, incident_id: str) -> None:
        self.incidents.ignore(incident_id)

    def delete(self, incident_id: str) -> None:
        self.incidents.delete(incident_id)
