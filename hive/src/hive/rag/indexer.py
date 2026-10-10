from hashlib import sha256

from langchain_text_splitters import RecursiveCharacterTextSplitter

from hive.infrastructure.config import Settings
from hive.persistence.database import Database
from hive.rag.embeddings import OpenAIEmbeddings
from hive.rag.persistence import RagRepository
from hive.rag.s3 import S3KnowledgeSource


class RagIndexer:
    def __init__(self, settings: Settings, database: Database):
        if not settings.rag.enabled:
            raise RuntimeError("RAG is disabled in Hive configuration")
        if settings.rag.embedding_dimensions != 1536:
            raise ValueError("Hive RAG schema requires 1536-dimensional embeddings")
        self.settings = settings
        self.repository = RagRepository(database)
        self.embeddings = OpenAIEmbeddings(
            settings.rag_openai_api_key,
            settings.rag.embedding_model,
            settings.rag.embedding_dimensions,
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=3000,
            chunk_overlap=400,
            separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
        )

    def run(self) -> int:
        indexed = 0
        for source_config in self.settings.rag.sources:
            source = S3KnowledgeSource(
                self.settings.rag,
                source_config,
                self.settings.rag_s3_access_key_id,
                self.settings.rag_s3_secret_access_key,
            )
            try:
                source_keys: set[str] = set()
                for key, etag in source.objects():
                    source_keys.add(key)
                    content = source.read(key)
                    checksum = sha256(content.encode()).hexdigest()
                    if self.repository.unchanged(
                        source_config.domain.value,
                        source_config.repository,
                        key,
                        etag,
                        checksum,
                    ):
                        continue
                    chunks = self.splitter.split_text(content)
                    embeddings = self.embeddings.embed(chunks)
                    self.repository.replace_document(
                        source_config.domain.value,
                        source_config.repository,
                        key,
                        etag,
                        checksum,
                        chunks,
                        embeddings,
                    )
                    indexed += 1
                self.repository.delete_missing(
                    source_config.domain.value,
                    source_config.repository,
                    source_config.prefix,
                    source_keys,
                )
            finally:
                source.close()
        self.repository.delete_unconfigured_sources(
            [(source.domain.value, source.repository, source.prefix) for source in self.settings.rag.sources]
        )
        return indexed

    def close(self) -> None:
        self.embeddings.close()
