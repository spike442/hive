"""Authentication for Hive's control API."""

from fastapi import Header, HTTPException, Request


def bearer_token_is_valid(authorization: str | None, expected_token: str) -> bool:
    return bool(expected_token and authorization == f"Bearer {expected_token}")


def require_control_auth(request: Request, authorization: str | None = Header(default=None)) -> None:
    token = request.app.state.runtime.settings.control_token
    if not bearer_token_is_valid(authorization, token):
        raise HTTPException(status_code=401, detail="invalid Hive control authorization")
