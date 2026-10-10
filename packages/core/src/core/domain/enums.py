from enum import StrEnum


class AgentDomain(StrEnum):
    SRE = "sre"
    PULL_REQUEST_REVIEW = "pr-review"


class AgentStatus(StrEnum):
    ACTIVE = "active"
    IDLE = "idle"
    DOWN = "down"


class IncidentStatus(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    PENDING = "pending"
    PROCESSING = "processing"
    FAILED = "failed"
    BLOCKED = "blocked"
    PR_CREATED = "pr_created"
    IGNORED = "ignored"
    RESOLVED = "resolved"


class DiagnosisStatus(StrEnum):
    OBSERVED = "observed"
    INVESTIGATING = "investigating"
    PROPOSED = "proposed"
    BLOCKED = "blocked"
    VERIFIED = "verified"


class IncidentEvent(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    CREATED = "created"
    REOPENED = "reopened"
    REPLAYED = "replayed"
    PROCESSING = "processing"
    PENDING = "pending"
    FAILED = "failed"
    BLOCKED = "blocked"
    PR_CREATED = "pr_created"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    MANUAL_ACTION_EXECUTED = "manual_action_executed"


class ReviewStatus(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    PENDING = "pending"
    PROCESSING = "processing"
    DECIDED = "decided"
    FAILED = "failed"
    MERGED = "merged"


class ActionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AuditStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertSource(StrEnum):
    GATUS = "gatus"
    ALERTMANAGER = "alertmanager"


class AlertStatus(StrEnum):
    FIRING = "firing"
    RESOLVED = "resolved"


class GatusEventStatus(StrEnum):
    TRIGGERED = "TRIGGERED"
    RESOLVED = "RESOLVED"
