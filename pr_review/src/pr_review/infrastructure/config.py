from pathlib import Path

from core.config.models import LoggingConfig, TemporalConnectionConfig, YamlSettings
from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict


class ReviewConfig(BaseModel):
    merge_enabled: bool
    allowed_risk_levels: set[str]
    allowed_confidence_levels: set[str]
    command_timeout_seconds: int
    max_diff_bytes: int
    max_tool_calls: int
    max_tool_output_bytes: int
    workspace_root: Path


class LLMConfig(BaseModel):
    base_url: str
    model: str
    prompt_cache_key: str
    max_retries: int


class RepositoryToolConfig(BaseModel):
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")


class RepositoryConfig(BaseModel):
    owner: str
    name: str
    clone_url: str
    clone_depth: int
    tools: list[RepositoryToolConfig]


class S3Config(BaseModel):
    bucket: str
    prefix: str
    system_key: str
    action_prompt_prefix: str
    endpoint_url: str
    region: str
    max_bytes: int


class TemporalConfig(TemporalConnectionConfig):
    task_queue: str


class Settings(YamlSettings):
    model_config = SettingsConfigDict(
        yaml_file=[
            "/etc/pr-review/config.yaml",
            "/etc/pr-review/llm.yaml",
            "pr_review/infra/config/config.yaml",
            "pr_review/infra/config/llm.yaml",
            "infra/config/config.yaml",
            "infra/config/llm.yaml",
        ],
        env_prefix="PR_REVIEW_",
        env_nested_delimiter="__",
        extra="forbid",
    )

    logging: LoggingConfig
    review: ReviewConfig
    llm: LLMConfig
    s3: S3Config
    temporal: TemporalConfig
    s3_access_key_id: str = Field(min_length=1, validation_alias="PR_REVIEW_S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(min_length=1, validation_alias="PR_REVIEW_S3_SECRET_ACCESS_KEY")
    openai_api_key: str = Field(min_length=1, validation_alias="PR_REVIEW_LLM_API_KEY")
