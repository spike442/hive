import json

from core.domain import RetrievedContext

from hive.infrastructure.config import Settings
from hive.persistence.database import Database
from hive.rag.embeddings import OpenAIEmbeddings
from hive.rag.persistence import RagRepository


class RagRetriever:
    def __init__(self, settings: Settings, database: Database):
        self.max_results = settings.rag.max_results
        self.repository = RagRepository(database)
        self.embeddings = OpenAIEmbeddings(
            settings.rag_openai_api_key,
            settings.rag.embedding_model,
            settings.rag.embedding_dimensions,
        )

    def retrieve(self, domain: str, repository: str, query: str) -> list[RetrievedContext]:
        embedding = self.embeddings.embed([query])[0]
        rows = self.repository.search(
            domain,
            repository,
            embedding,
            query,
            self.max_results,
        )
        return [
            RetrievedContext(
                content=str(row["content"]),
                source=f"{row['object_key']}#chunk",
                score=float(row["semantic_score"]),
            )
            for row in rows
        ]

    @staticmethod
    def query_text(value: object) -> str:
        return json.dumps(value, sort_keys=True, default=str)

    def close(self) -> None:
        self.embeddings.close()
