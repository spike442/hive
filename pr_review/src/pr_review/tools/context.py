from dataclasses import dataclass

from core.observability.audit import AuditLog

from pr_review.integrations.command_executor import CommandExecutor


@dataclass(frozen=True)
class ToolContext:
    executor: CommandExecutor
    audit: AuditLog
