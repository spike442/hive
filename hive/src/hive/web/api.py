from core.domain import AgentDomain, AgentStatus
from fastapi import APIRouter, Header, HTTPException, Request

from hive.web.auth import require_control_auth

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
def list_agents(request: Request) -> dict[str, list[dict]]:
    agents = request.app.state.runtime.agent_service.list_agents()
    return {"agents": [agent.model_dump(mode="json") for agent in agents]}


@router.get("/{domain}")
def agent_status(domain: AgentDomain, request: Request) -> dict:
    try:
        return request.app.state.runtime.agent_service.status(domain).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="agent not configured") from exc


@router.post("/{domain}/idle")
def set_idle(domain: AgentDomain, request: Request, authorization: str | None = Header(default=None)) -> dict:
    require_control_auth(request, authorization)
    return _set_status(domain, request, AgentStatus.IDLE)


@router.post("/{domain}/active")
def set_active(domain: AgentDomain, request: Request, authorization: str | None = Header(default=None)) -> dict:
    require_control_auth(request, authorization)
    return _set_status(domain, request, AgentStatus.ACTIVE)


def _set_status(domain: AgentDomain, request: Request, status: AgentStatus) -> dict:
    try:
        return request.app.state.runtime.agent_service.set_status(domain, status).model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="agent not configured") from exc
