from core.domain import AgentDomain
from fastapi import APIRouter, Header, HTTPException, Query, Request

from hive.web.auth import require_control_auth

router = APIRouter(tags=["pr-review"])


def _runtime(request: Request):
    try:
        return request.app.state.runtime.agents[AgentDomain.PULL_REQUEST_REVIEW]
    except KeyError as exc:
        raise HTTPException(status_code=503, detail="PR review is disabled or has no runtime") from exc


@router.post("/events/reviews/check", status_code=202)
async def check_reviews(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    require_control_auth(request, authorization)
    workflow_id = await _runtime(request).service.check_now()
    return {"status": "accepted", "workflow_id": workflow_id}


@router.get("/reviews")
def reviews(
    request: Request,
    limit: int = Query(default=100, ge=1, le=200),
    status: str | None = Query(default=None),
) -> dict:
    return {"reviews": _runtime(request).service.list_reviews(limit, status)}


@router.delete("/reviews/{review_id}", status_code=202)
def delete_review(
    review_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    require_control_auth(request, authorization)
    _runtime(request).service.delete(review_id)
    return {"status": "deleted"}


@router.post("/reviews/{review_id}/retry", status_code=202)
async def retry_review(
    review_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    require_control_auth(request, authorization)
    try:
        workflow_id = await _runtime(request).service.retry(review_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "accepted", "workflow_id": workflow_id}
