from dataclasses import dataclass

from core.observability.audit import AuditLog

from sre.infrastructure.config import Settings
from sre.integrations.command_executor import CommandExecutor


@dataclass(frozen=True)
class ToolContext:
    settings: Settings
    executor: CommandExecutor
    audit: AuditLog
