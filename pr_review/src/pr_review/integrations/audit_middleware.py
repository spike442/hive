from typing import Any

from core.domain import AuditStatus
from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain_core.messages import AIMessage, ToolMessage


class ReviewAuditMiddleware(AgentMiddleware):
    """Persist model and tool activity without coupling tools to storage."""

    def wrap_model_call(self, request, handler):
        try:
            response = handler(request)
        except Exception as exc:
            request.runtime.context.audit.record_model_response(None, status=AuditStatus.FAILED.value)
            request.runtime.context.audit.actions[-1].details["error"] = type(exc).__name__
            raise
        messages = getattr(response, "result", [response])
        for message in messages:
            if not isinstance(message, AIMessage):
                continue
            request.runtime.context.audit.record_model_response(
                message.response_metadata.get("id"), message.usage_metadata
            )
        return response

    def wrap_tool_call(self, request: ToolCallRequest, handler) -> Any:
        details = {
            "call_id": request.tool_call.get("id"),
            "tool": request.tool_call.get("name"),
            "arguments": request.tool_call.get("args", {}),
        }
        try:
            result = handler(request)
        except Exception as exc:
            details.update({"status": AuditStatus.FAILED.value, "error": type(exc).__name__})
            request.runtime.context.audit.record_tool_result(details)
            raise
        if isinstance(result, ToolMessage):
            details.update({"output": result.content, "status": result.status})
        request.runtime.context.audit.record_tool_result(details)
        return result
