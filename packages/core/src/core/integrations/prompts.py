"""Standard S3-backed prompt loading for Hive agents."""

import hashlib
from dataclasses import dataclass

import boto3


@dataclass(frozen=True)
class Prompt:
    text: str
    etag: str


@dataclass(frozen=True)
class PromptStoreConfig:
    bucket: str
    prefix: str
    endpoint: str
    region: str
    access_key_id: str
    secret_access_key: str
    reload_on_change: bool
    max_bytes: int


class PromptStore:
    """Load prompt text from one S3 prefix with optional ETag reloading."""

    def __init__(self, config: PromptStoreConfig) -> None:
        self.bucket = config.bucket
        self.prefix = config.prefix.strip("/")
        self.reload_on_change = config.reload_on_change
        self.max_bytes = config.max_bytes
        self.client = boto3.client(
            "s3",
            endpoint_url=config.endpoint,
            region_name=config.region,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
        )
        self._cache: dict[str, Prompt] = {}

    def text(self, key: str, expected_sha256: str = "") -> str:
        prompt = self._load(key)
        if expected_sha256 and hashlib.sha256(prompt.text.encode()).hexdigest() != expected_sha256:
            raise RuntimeError(f"prompt checksum does not match: {key}")
        return prompt.text

    def version(self, keys: list[str]) -> str:
        loaded = [self._load(key) for key in keys]
        identity = "|".join(f"{key}:{prompt.etag}" for key, prompt in zip(keys, loaded, strict=True))
        return hashlib.sha256(identity.encode()).hexdigest()[:16]

    def close(self) -> None:
        self.client.close()

    def _load(self, key: str) -> Prompt:
        normalized_key = self._key(key)
        cached = self._cache.get(normalized_key)
        if cached is not None and not self.reload_on_change:
            return cached

        etag = self._etag(normalized_key) if self.reload_on_change else ""
        if cached is not None and cached.etag == etag:
            return cached

        response = self.client.get_object(Bucket=self.bucket, Key=normalized_key)
        body = response["Body"]
        try:
            content = body.read(self.max_bytes + 1)
        finally:
            body.close()
        if len(content) > self.max_bytes:
            raise RuntimeError(f"prompt is too large: {key}")
        loaded = Prompt(
            text=content.decode("utf-8"),
            etag=etag or str(response.get("ETag", "")).strip('"'),
        )
        self._cache[normalized_key] = loaded
        return loaded

    def _etag(self, key: str) -> str:
        metadata = self.client.head_object(Bucket=self.bucket, Key=key)
        return str(metadata.get("ETag", "")).strip('"')

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key.lstrip('/')}" if self.prefix else key.lstrip("/")
