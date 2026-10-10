"""Configuration models shared by Hive services."""

from typing import Self

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, YamlConfigSettingsSource


class YamlSettings(BaseSettings):
    """Base settings type with the project's YAML-before-file-secret order."""

    @classmethod
    def load(cls) -> Self:
        return cls()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, env_settings, YamlConfigSettingsSource(settings_cls), file_secret_settings


class LoggingConfig(BaseModel):
    level: str


class KafkaConfig(BaseModel):
    bootstrap_servers: str
    security_protocol: str
    sasl_mechanisms: str
    consumer_group: str
    max_poll_interval_seconds: int = Field(gt=0)

    def client(self, username: str, password: str) -> dict[str, str]:
        return {
            "bootstrap.servers": self.bootstrap_servers,
            "security.protocol": self.security_protocol,
            "sasl.mechanisms": self.sasl_mechanisms,
            "sasl.username": username,
            "sasl.password": password,
        }


class TemporalConnectionConfig(BaseModel):
    address: str
    namespace: str
