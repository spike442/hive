from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from core.domain import DiagnosisStatus, IncidentStatus, RetrievedContext
from core.observability.audit import AuditLog
from core.observability.logging import log_payload

from sre.domain.diagnosis import Diagnosis
from sre.domain.incident import Incident, incident_id_from_alert

if TYPE_CHECKING:
    from sre.bootstrap.runtime import Runtime

logger = logging.getLogger(__name__)


def _replay_history(incident: Incident) -> str:
    """Build a compact, explicit context block for an operator replay."""
    lines = ["Previous attempts for this incident:"]
    for prompt in incident.replay_prompts:
        lines.append(f"- Operator replay instruction: {prompt}")
    for entry in incident.diagnosis_history[-5:]:
        diagnosis = entry.get("diagnosis", {})
        lines.append(f"- Diagnosis at {entry.get('at', 'unknown')}: status={diagnosis.get('status', 'unknown')}")
        if diagnosis.get("hypothesis"):
            lines.append(f"  hypothesis: {diagnosis['hypothesis']}")
        if diagnosis.get("proposed_files"):
            lines.append(f"  proposed files: {', '.join(diagnosis['proposed_files'])}")
        if diagnosis.get("manual_actions"):
            lines.append("  manual actions were proposed")
    return "\n".join(lines)


def _start_incident(
    incident_id: str,
    alert: dict[str, Any],
    prior_incident: Incident | None,
    replay_prompt: str | None,
) -> Incident:
    attempts = prior_incident.attempts + 1 if prior_incident else 1
    replay_prompts = list(prior_incident.replay_prompts) if prior_incident else []
    if replay_prompt:
        replay_prompts.append(replay_prompt)
    return Incident(
        id=incident_id,
        status=IncidentStatus.PROCESSING,
        alert=alert,
        diagnosis=Diagnosis(),
        attempts=attempts,
        replayed_at=datetime.now(UTC).isoformat() if prior_incident else None,
        replay_prompts=replay_prompts,
        manual_actions=list(prior_incident.manual_actions) if prior_incident else [],
        diagnosis_history=list(prior_incident.diagnosis_history) if prior_incident else [],
        timeline=list(prior_incident.timeline) if prior_incident else [],
        audit_actions=list(prior_incident.audit_actions) if prior_incident else [],
    )


def investigate_incident(
    runtime: Runtime,
    alert: dict[str, Any],
    rag_context: list[RetrievedContext],
    replay_prompt: str | None = None,
    prior_incident: Incident | None = None,
) -> Incident:
    """Investigate an incident and return a diagnosis for Hive to execute."""
    incident_id = incident_id_from_alert(alert)
    audit = AuditLog()
    incident = _start_incident(incident_id, alert, prior_incident, replay_prompt)
    logger.info("incident investigation started incident_id=%s", incident_id)
    try:
        result = runtime.repository.sync_repository()
        audit.record("repository_sync", result)
        logger.info("incident.step output step=repository_sync result=%s", log_payload(result))

        operator_prompt = replay_prompt
        if prior_incident:
            history = _replay_history(prior_incident)
            operator_prompt = f"{history}\n\n{operator_prompt}" if operator_prompt else history
        diagnosis = runtime.diagnosis.diagnose(incident, operator_prompt, audit, rag_context)
        logger.info(
            "incident.step output incident_id=%s step=diagnosis result=%s",
            incident.id,
            log_payload(diagnosis.model_dump()),
        )
        logger.info(
            "incident investigated incident=%s risk=%s confidence=%s",
            diagnosis.incident,
            diagnosis.risk,
            diagnosis.confidence,
        )
        incident.diagnosis = diagnosis
        incident.status = (
            IncidentStatus.BLOCKED if diagnosis.status is DiagnosisStatus.BLOCKED else IncidentStatus.PENDING
        )
    except Exception as exc:
        audit.record("workflow_failed", {"error": type(exc).__name__})
        incident.status = IncidentStatus.FAILED
        incident.diagnosis = Diagnosis(
            incident="alert investigation failed",
            hypothesis=f"The investigation could not complete: {type(exc).__name__}.",
            evidence=["The incident can be retried because no completed incident fix was recorded."],
            validation=["No fix was proposed."],
            rollback="No change was made.",
        )
    incident.audit_actions.extend(audit.actions)
    return incident
