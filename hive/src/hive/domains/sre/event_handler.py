from typing import Any

from core.domain import AlertSource, AlertStatus


def alertmanager_alerts(event: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert Alertmanager event-recorder JSON into SRE alert payloads."""
    data = event.get("data") or {}
    if not isinstance(data, dict):
        return []
    if created := data.get("alertCreated") or data.get("alert_created"):
        return [_alert(created.get("alert", created), resolved=False)]
    if resolved := data.get("alertResolved") or data.get("alert_resolved"):
        return [_alert(resolved.get("alert", resolved), resolved=True)]
    return []


def _alert(value: dict[str, Any], resolved: bool) -> dict[str, Any]:
    details = value.get("details") or value
    labels = dict(details.get("labels", {}))
    if details.get("name") and "alertname" not in labels:
        labels["alertname"] = details["name"]
    labels.setdefault("source", AlertSource.ALERTMANAGER.value)
    alert = {
        "status": AlertStatus.RESOLVED.value if resolved else AlertStatus.FIRING.value,
        "labels": labels,
        "annotations": details.get("annotations", {}),
        "startsAt": details.get("startsAt") or details.get("starts_at", ""),
        "endsAt": details.get("endsAt") or details.get("ends_at", ""),
        "fingerprint": str(value.get("fingerprint") or details.get("fingerprint", "")),
    }
    if not alert["fingerprint"]:
        raise ValueError("Alertmanager event is missing its fingerprint")
    return alert
