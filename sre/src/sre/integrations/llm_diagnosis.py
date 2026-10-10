import logging

from core.domain import RetrievedContext
from core.integrations.prompts import PromptStore
from core.observability.audit import AuditLog
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI

from sre.domain.diagnosis import Diagnosis
from sre.domain.incident import Incident
from sre.infrastructure.config import Settings
from sre.integrations.audit_middleware import DiagnosisAuditMiddleware
from sre.integrations.command_executor import CommandExecutor
from sre.tools.context import ToolContext
from sre.tools.registry import resolve_tools

logger = logging.getLogger(__name__)


class LangChainDiagnosisEngine:
    def __init__(self, settings: Settings, prompts: PromptStore, executor: CommandExecutor):
        self.settings = settings
        self.prompts = prompts
        self.executor = executor
        self.model = ChatOpenAI(
            model=settings.llm.model,
            api_key=settings.openai_api_key,
            base_url=settings.llm.base_url,
            max_retries=2,
            use_responses_api=True,
            output_version="responses/v1",
        )
        investigation_prompt = prompts.text("actions/investigate.md")
        tool_prompts = "\n\n".join(
            f"{tool.name} instructions:\n{prompts.text(f'actions/{tool.name}.md')}" for tool in settings.llm.tools
        )
        self.agent = create_agent(
            model=self.model.bind(prompt_cache_key=settings.llm.prompt_cache_key),
            tools=resolve_tools(settings.llm.tools),
            context_schema=ToolContext,
            system_prompt=(
                f"{prompts.text(settings.s3.system_key, settings.s3.prompt_sha256)}\n\n"
                f"Investigation instructions:\n{investigation_prompt}\n\n{tool_prompts}"
            ),
            response_format=ToolStrategy(Diagnosis),
            middleware=[
                ToolCallLimitMiddleware(run_limit=settings.limits.max_tool_calls, exit_behavior="error"),
                DiagnosisAuditMiddleware(),
            ],
        )

    def diagnose(
        self,
        incident: Incident,
        replay_prompt: str | None,
        audit: AuditLog,
        rag_context: list[RetrievedContext],
    ) -> Diagnosis:
        try:
            result = self.agent.invoke(
                {"messages": [{"role": "user", "content": self._request(incident, replay_prompt, rag_context)}]},
                config={
                    "run_name": f"sre-investigation-{incident.id}",
                    "tags": ["sre", str(incident.alert.get("source", "unknown"))],
                    "metadata": {"incident_id": incident.id},
                },
                context=ToolContext(
                    settings=self.settings,
                    executor=self.executor,
                    audit=audit,
                ),
            )
            diagnosis = result.get("structured_response")
            if not isinstance(diagnosis, Diagnosis):
                raise ValueError("LangChain did not return a structured diagnosis")
            audit.record("diagnosis_completed", diagnosis.model_dump(mode="json"))
            return diagnosis
        except Exception as exc:
            logger.warning("SRE diagnosis failed incident_id=%s error=%s", incident.id, type(exc).__name__)
            audit.record("diagnosis_failed", {"error": type(exc).__name__})
            return Diagnosis(
                incident="investigation failed",
                hypothesis="The diagnosis could not be completed.",
                evidence=["The LangChain diagnosis engine failed before a valid fix was returned."],
                validation=["No validation was run."],
                rollback="No change was proposed.",
            )

    def _request(
        self,
        incident: Incident,
        replay_prompt: str | None,
        rag_context: list[RetrievedContext],
    ) -> str:
        request = "Investigate this alert and follow the diagnosis workflow.\n\nAlert:\n" + str(incident.alert)
        if rag_context:
            request += (
                "\n\nRetrieved reference material (verify against current repository and cluster state):\n"
                + "\n\n".join(f"Source: {item.source}\n{item.content}" for item in rag_context)
            )
        if replay_prompt:
            template = self.prompts.text("actions/replay.md")
            request += "\n\n" + template.replace("{{operator_prompt}}", replay_prompt)
        return request

    def close(self) -> None:
        self.model.root_client.close()
        self.prompts.close()
