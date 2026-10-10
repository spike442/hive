from core.domain import AgentDomain, IncidentStatus
from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel

from hive.web.auth import require_control_auth

router = APIRouter(tags=["sre"])


class ReplayRequest(BaseModel):
    prompt: str | None = None


class ManualActionRequest(BaseModel):
    action_index: int


def _service(request: Request):
    try:
        return request.app.state.runtime.agents[AgentDomain.SRE].service
    except KeyError as exc:
        raise HTTPException(status_code=503, detail="SRE is disabled or has no runtime") from exc


def _require_incident(request: Request, incident_id: str) -> dict:
    found = _service(request).get_incident(incident_id)
    if not found:
        raise HTTPException(status_code=404, detail="incident not found")
    return found


@router.get("/incidents")
def incidents(
    request: Request,
    limit: int = Query(default=200, ge=1, le=500),
    source: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict:
    return {"incidents": _service(request).list_incidents(limit, source, status)}


@router.get("/incidents/{incident_id}")
def incident(incident_id: str, request: Request) -> dict:
    return _require_incident(request, incident_id)


@router.post("/incidents/replay/{incident_id}", status_code=202)
async def replay_incident(
    incident_id: str,
    request: Request,
    replay: ReplayRequest | None = None,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    require_control_auth(request, authorization)
    try:
        workflow_id = await _service(request).replay(
            incident_id,
            replay.prompt.strip() if replay and replay.prompt else "",
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="incident not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "accepted", "workflow_id": workflow_id}


@router.post("/incidents/{incident_id}/ignore", status_code=202)
def ignore_incident(
    incident_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    require_control_auth(request, authorization)
    try:
        _service(request).ignore(incident_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="incident not found") from exc
    return {"status": IncidentStatus.IGNORED.value}


@router.post("/incidents/{incident_id}/manual-actions/execute", status_code=202)
async def execute_manual_action(
    incident_id: str,
    request: Request,
    action: ManualActionRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    require_control_auth(request, authorization)
    incident = _require_incident(request, incident_id)
    actions = incident.get("diagnosis", {}).get("manual_actions", [])
    if action.action_index < 0 or action.action_index >= len(actions):
        raise HTTPException(status_code=404, detail="manual action not found")
    workflow_id = await _service(request).execute_manual_action(incident_id, action.action_index)
    return {"status": "accepted", "action_index": str(action.action_index), "workflow_id": workflow_id}


@router.delete("/incidents/{incident_id}", status_code=202)
def delete_incident(
    incident_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    require_control_auth(request, authorization)
    try:
        _service(request).delete(incident_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="incident not found") from exc
    return {"status": "deleted"}
