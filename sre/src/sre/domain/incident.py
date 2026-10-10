from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.domain import AlertSource, IncidentStatus
from core.observability.audit import AuditAction

from sre.domain.diagnosis import Diagnosis


def normalize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    """Keep alert payloads intact while dropping empty timestamp values."""
    normalized = dict(alert)
    for field_name, value in list(normalized.items()):
        if not field_name.endswith("At") or not isinstance(value, str):
            continue
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            continue
        if timestamp == datetime.min.replace(tzinfo=timestamp.tzinfo):
            normalized.pop(field_name)
    return normalized


@dataclass
class Incident:
    id: str
    status: IncidentStatus
    alert: dict[str, Any]
    diagnosis: Diagnosis
    pull_request_url: str | None = None
    attempts: int = 0
    updated_at: str | None = None
    replayed_at: str | None = None
    replay_prompts: list[str] = field(default_factory=list)
    manual_actions: list[dict[str, Any]] = field(default_factory=list)
    diagnosis_history: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    audit_actions: list[AuditAction] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "alert": normalize_alert(self.alert),
            "diagnosis": self.diagnosis.model_dump(mode="json"),
            "pull_request_url": self.pull_request_url,
            "attempts": self.attempts,
            "updated_at": self.updated_at,
            "replayed_at": self.replayed_at,
            "replay_prompts": self.replay_prompts,
            "manual_actions": self.manual_actions,
            "diagnosis_history": self.diagnosis_history,
            "timeline": self.timeline,
            "audit_actions": [action.model_dump(mode="json") for action in self.audit_actions],
        }


def incident_id_from_alert(alert: dict[str, Any]) -> str:
    """Derive the stable incident identity from its source alert."""
    labels = alert.get("labels", {})
    if labels.get("source") == AlertSource.GATUS:
        endpoint = labels.get("name") or labels.get("endpoint") or "unknown"
        group = labels.get("group") or "unknown"
        return f"gatus:{group}:{endpoint}"
    fingerprint = alert.get("fingerprint")
    if not fingerprint:
        raise ValueError("Alertmanager alert is missing its fingerprint")
    return str(fingerprint)
