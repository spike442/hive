from pathlib import Path
from urllib.parse import quote

from core.config.models import KafkaConfig, LoggingConfig, TemporalConnectionConfig, YamlSettings
from core.domain import AgentConfig, AgentDomain
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import SettingsConfigDict


class HealthConfig(BaseModel):
    timeout_seconds: float


class DatabaseConfig(BaseModel):
    host: str
    port: int
    name: str
    user: str


class ApiConfig(BaseModel):
    allowed_origins: list[str]


class UiConfig(BaseModel):
    hive_url: str


class GitHubConfig(BaseModel):
    api_url: str
    merge_method: str


class TemporalConfig(TemporalConnectionConfig):
    workflow_task_queue: str
    sre_task_queue: str
    pr_review_task_queue: str
    metrics_bind_address: str


class RepositoryConfig(BaseModel):
    owner: str
    name: str
    clone_url: str
    clone_depth: int
    tools: list[dict[str, str]]


class IncidentConfig(BaseModel):
    repository: str
    path: Path
    branch: str
    branch_prefix: str
    version: str
    commit_author_name: str
    commit_author_email: str
    secret_material_patterns: list[str]


class ExecutionConfig(BaseModel):
    working_directory: Path
    command_timeout_seconds: int
    max_output_bytes: int


class RagSourceConfig(BaseModel):
    domain: AgentDomain
    repository: str
    prefix: str


class RagConfig(BaseModel):
    enabled: bool
    endpoint: str
    region: str
    bucket: str
    embedding_model: str
    embedding_dimensions: int = Field(gt=0)
    max_results: int = Field(gt=0)
    sources: list[RagSourceConfig]


class Settings(YamlSettings):
    model_config = SettingsConfigDict(
        yaml_file=[
            "/etc/hive/config.yaml",
            "/etc/hive/repositories.yaml",
            "hive/infra/config/config.yaml",
            "hive/infra/config/repositories.yaml",
            "infra/config/config.yaml",
            "infra/config/repositories.yaml",
        ],
        env_prefix="HIVE_",
        env_nested_delimiter="__",
        extra="forbid",
    )

    logging: LoggingConfig
    health: HealthConfig
    agents: list[AgentConfig]
    database: DatabaseConfig
    api: ApiConfig
    ui: UiConfig
    kafka: KafkaConfig
    temporal: TemporalConfig
    github: GitHubConfig
    repositories: list[RepositoryConfig]
    incident: IncidentConfig
    execution: ExecutionConfig
    rag: RagConfig
    control_token: str = Field(min_length=1, validation_alias="HIVE_CONTROL_TOKEN")
    database_password: str = Field(min_length=1, validation_alias="HIVE_DATABASE_PASSWORD")
    discord_webhook_url: str = Field(min_length=1, validation_alias="HIVE_DISCORD_WEBHOOK_URL")
    kafka_username: str = Field(min_length=1, validation_alias="HIVE_KAFKA_USERNAME")
    kafka_password: str = Field(min_length=1, validation_alias="HIVE_KAFKA_PASSWORD")
    github_app_id: str = Field(min_length=1, validation_alias="HIVE_GITHUB_APP_ID")
    github_installation_id: str = Field(min_length=1, validation_alias="HIVE_GITHUB_INSTALLATION_ID")
    github_private_key: str = Field(min_length=1, validation_alias="HIVE_GITHUB_APP_PRIVATE_KEY")
    rag_s3_access_key_id: str = Field(min_length=1, validation_alias="HIVE_RAG_S3_ACCESS_KEY_ID")
    rag_s3_secret_access_key: str = Field(min_length=1, validation_alias="HIVE_RAG_S3_SECRET_ACCESS_KEY")
    rag_openai_api_key: str = Field(min_length=1, validation_alias="HIVE_RAG_OPENAI_API_KEY")

    @model_validator(mode="after")
    def validate_agents(self) -> "Settings":
        domains = [agent.domain for agent in self.agents]
        if len(domains) != len(set(domains)):
            raise ValueError("agent domains must be unique")
        return self

    @property
    def database_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{quote(self.database.user)}:{quote(self.database_password)}"
            f"@{self.database.host}:{self.database.port}/{quote(self.database.name)}"
        )
