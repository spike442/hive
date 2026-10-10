from pydantic import BaseModel, Field

from core.domain.enums import AgentDomain, AgentStatus


class AgentConfig(BaseModel):
    """Configuration for an agent managed by the Hive platform."""

    domain: AgentDomain
    base_url: str
    job_interval_seconds: int | None = Field(gt=0)


class Agent(BaseModel):
    """Current runtime status of an agent managed by Hive."""

    domain: AgentDomain
    status: AgentStatus
    healthy: bool
    version: str = ""
