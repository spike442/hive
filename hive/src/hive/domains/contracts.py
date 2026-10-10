from typing import Protocol

from core.domain import AgentConfig


class DomainRuntime(Protocol):
    config: AgentConfig
    service: object
    activities: object
