from core.domain import AgentDomain
from core.orchestration import ActivityName
from hive.application.agent_service import AgentService
from temporalio import activity


class AgentStatusActivities:
    def __init__(self, agents: AgentService):
        self.agents = agents

    @activity.defn(name=ActivityName.AGENT_IS_ACTIVE.value)
    def is_active(self, domain: str) -> bool:
        return self.agents.is_active(AgentDomain(domain))
