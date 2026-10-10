from collections.abc import Iterator

import boto3

from hive.infrastructure.config import RagConfig, RagSourceConfig


class S3KnowledgeSource:
    def __init__(self, config: RagConfig, source: RagSourceConfig, access_key_id: str, secret_access_key: str):
        self.source = source
        self.client = boto3.client(
            "s3",
            endpoint_url=config.endpoint,
            region_name=config.region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )
        self.bucket = config.bucket

    def objects(self) -> Iterator[tuple[str, str]]:
        token = None
        while True:
            request = {"Bucket": self.bucket, "Prefix": self.source.prefix.strip("/") + "/"}
            if token:
                request["ContinuationToken"] = token
            response = self.client.list_objects_v2(**request)
            for item in response.get("Contents", []):
                key = str(item["Key"])
                if not key.endswith("/"):
                    yield key, str(item["ETag"]).strip('"')
            if not response.get("IsTruncated", False):
                return
            token = str(response["NextContinuationToken"])

    def read(self, key: str) -> str:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        with response["Body"] as body:
            return body.read().decode("utf-8")

    def close(self) -> None:
        self.client.close()
