from dataclasses import dataclass

from core.integrations.prompts import PromptStore, PromptStoreConfig

from sre.infrastructure.config import Settings
from sre.integrations.command_executor import CommandExecutor
from sre.integrations.llm_diagnosis import LangChainDiagnosisEngine
from sre.integrations.repository import RepositorySync


@dataclass
class Runtime:
    """Already-built SRE resources shared for the process lifetime."""

    repository: RepositorySync
    diagnosis: LangChainDiagnosisEngine


def build_runtime(settings: Settings) -> Runtime:
    prompts = PromptStore(
        PromptStoreConfig(
            bucket=settings.s3.bucket,
            prefix=settings.s3.prompt_prefix,
            endpoint=settings.s3.endpoint,
            region=settings.s3.region,
            access_key_id=settings.s3.access_key_id,
            secret_access_key=settings.s3.secret_access_key,
            reload_on_change=False,
            max_bytes=settings.s3.max_bytes,
        )
    )
    repository = RepositorySync(settings)
    diagnosis = LangChainDiagnosisEngine(settings, prompts, CommandExecutor(settings))
    return Runtime(repository=repository, diagnosis=diagnosis)
