from core.domain import IncidentStatus, RetrievedContext
from core.observability.audit import AuditAction

from sre.application.workflow import investigate_incident
from sre.domain.diagnosis import Diagnosis
from sre.domain.incident import Incident


def replay_incident(
    runtime,
    incident_id: str,
    prompt: str,
    incident_data: dict,
    rag_context: list[RetrievedContext],
) -> dict:
    incident = Incident(
        id=incident_id,
        status=IncidentStatus(incident_data["status"]),
        alert=incident_data["alert"],
        diagnosis=Diagnosis.model_validate(incident_data["diagnosis"]),
        attempts=incident_data.get("attempts", 0),
        replay_prompts=incident_data.get("replay_prompts", []),
        manual_actions=incident_data.get("manual_actions", []),
        diagnosis_history=incident_data.get("diagnosis_history", []),
        timeline=incident_data.get("timeline", []),
        audit_actions=[AuditAction.model_validate(action) for action in incident_data.get("audit_actions", [])],
    )
    if incident.status not in {IncidentStatus.ACKNOWLEDGED, IncidentStatus.FAILED, IncidentStatus.BLOCKED}:
        raise RuntimeError(f"incident cannot be replayed from {incident.status.value}")
    return investigate_incident(
        runtime,
        incident.alert,
        rag_context,
        prompt or None,
        prior_incident=incident,
    ).as_dict()
