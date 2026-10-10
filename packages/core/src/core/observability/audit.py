from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from core.domain import AuditStatus


class AuditAction(BaseModel):
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class AuditLog:
    """Collect typed model and tool actions for one agent execution."""

    def __init__(self) -> None:
        self.actions: list[AuditAction] = []

    def record(self, action: str, details: dict[str, Any]) -> None:
        self.actions.append(AuditAction(action=action, details=details, timestamp=datetime.now(UTC)))

    def record_model_response(
        self,
        response_id: str | None,
        usage: dict[str, Any] | None = None,
        status: str = AuditStatus.COMPLETED.value,
    ) -> None:
        details: dict[str, Any] = {"status": status}
        if response_id:
            details["response_id"] = response_id
        if usage:
            details["usage"] = usage
        self.record("llm_response", details)

    def record_tool_result(self, details: dict[str, Any]) -> None:
        self.record("tool_call", details)
