from pathlib import Path

from core.config.models import LoggingConfig, TemporalConnectionConfig, YamlSettings
from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict


class ShellConfig(BaseModel):
    allowed_binaries: list[str]
    denied_patterns: list[str]


class ToolConfig(BaseModel):
    name: str


class LLMConfig(BaseModel):
    base_url: str
    model: str
    prompt_cache_key: str
    tools: list[ToolConfig]
    shell: ShellConfig


class RepositoryConfig(BaseModel):
    url: str
    branch: str
    path: Path


class PrometheusConfig(BaseModel):
    url: str


class S3Config(BaseModel):
    endpoint: str
    region: str
    bucket: str
    prompt_prefix: str
    system_key: str
    prompt_sha256: str
    max_bytes: int
    access_key_id: str = Field(min_length=1)
    secret_access_key: str = Field(min_length=1)


class LimitsConfig(BaseModel):
    max_tool_calls: int


class TemporalConfig(TemporalConnectionConfig):
    task_queue: str


class Settings(YamlSettings):
    model_config = SettingsConfigDict(
        yaml_file=[
            "/etc/sre/config/config.yaml",
            "/etc/sre/config/llm.yaml",
            "infra/config/config.yaml",
            "infra/config/llm.yaml",
        ],
        env_prefix="SRE_",
        env_nested_delimiter="__",
        extra="forbid",
    )

    llm: LLMConfig
    logging: LoggingConfig
    repository: RepositoryConfig
    prometheus: PrometheusConfig
    s3: S3Config
    limits: LimitsConfig
    temporal: TemporalConfig
    openai_api_key: str = Field(min_length=1, validation_alias="SRE_LLM_API_KEY")
