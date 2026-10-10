import hashlib

from core.domain import AlertSource, AlertStatus, GatusEventStatus, IncidentStatus, RetrievedContext

from sre.application.workflow import investigate_incident
from sre.domain.incident import incident_id_from_alert, normalize_alert


def _gatus_alert(payload: dict) -> dict:
    status = GatusEventStatus(str(payload.get("status", "")).upper())
    group = str(payload.get("endpoint_group", "unknown"))
    name = str(payload.get("endpoint_name", "unknown"))
    description = str(payload.get("description", "Gatus endpoint alert"))
    url = str(payload.get("endpoint_url", ""))
    identity = f"gatus:{group}:{name}".encode()
    return {
        "status": AlertStatus.RESOLVED if status == GatusEventStatus.RESOLVED else AlertStatus.FIRING,
        "labels": {
            "alertname": "GatusEndpointAlert",
            "source": "gatus",
            "group": group,
            "name": name,
            "severity": "critical",
        },
        "annotations": {
            "summary": f"Gatus endpoint {name} is {status.value.lower()}",
            "description": f"{description} URL={url}".strip(),
        },
        "fingerprint": hashlib.sha256(identity).hexdigest()[:32],
    }


def process_alert_payload(
    runtime,
    payload: dict,
    source: AlertSource,
    rag_context: list[RetrievedContext],
) -> list[dict]:
    if source is AlertSource.GATUS:
        incoming_alerts = [_gatus_alert(payload)]
    else:
        incoming_alerts = payload.get("alerts")
        if not isinstance(incoming_alerts, list):
            raise ValueError("Alertmanager payload must contain alerts")

    results = []
    for alert in incoming_alerts:
        alert = {**normalize_alert(alert), "source": source.value}
        if alert.get("status") == AlertStatus.RESOLVED:
            results.append(
                {"id": incident_id_from_alert(alert), "status": IncidentStatus.RESOLVED.value, "alert": alert}
            )
            continue
        results.append(investigate_incident(runtime, alert, rag_context=rag_context).as_dict())
    return results
