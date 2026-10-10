import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text

from hive.persistence.database import Database


class RagRepository:
    def __init__(self, database: Database):
        self.database = database

    def unchanged(self, domain: str, repository: str, object_key: str, etag: str, checksum: str) -> bool:
        with self.database.sessions() as session:
            row = session.execute(
                text(
                    """
                    SELECT 1
                    FROM rag_documents
                    WHERE domain_name = :domain AND repository = :repository
                      AND object_key = :object_key
                      AND source_etag = :etag AND content_sha256 = :checksum
                    """
                ),
                {
                    "domain": domain,
                    "repository": repository,
                    "object_key": object_key,
                    "etag": etag,
                    "checksum": checksum,
                },
            ).first()
            return row is not None

    def replace_document(
        self,
        domain: str,
        repository: str,
        object_key: str,
        etag: str,
        checksum: str,
        content: list[str],
        embeddings: list[list[float]],
    ) -> None:
        document_id = uuid4()
        with self.database.sessions.begin() as session:
            current = session.execute(
                text(
                    """
                    SELECT id
                    FROM rag_documents
                    WHERE domain_name = :domain AND repository = :repository AND object_key = :object_key
                    """
                ),
                {"domain": domain, "repository": repository, "object_key": object_key},
            ).scalar_one_or_none()
            if current is not None:
                document_id = UUID(str(current))
                session.execute(
                    text("DELETE FROM rag_chunks WHERE document_id = :document_id"), {"document_id": document_id}
                )
                session.execute(
                    text(
                        """
                        UPDATE rag_documents
                        SET source_etag = :etag, content_sha256 = :checksum, indexed_at = :indexed_at
                        WHERE id = :document_id
                        """
                    ),
                    {
                        "document_id": document_id,
                        "etag": etag,
                        "checksum": checksum,
                        "indexed_at": datetime.now(UTC),
                    },
                )
            else:
                session.execute(
                    text(
                        """
                        INSERT INTO rag_documents
                            (id, domain_name, repository, object_key, source_etag, content_sha256, indexed_at)
                        VALUES (:id, :domain, :repository, :object_key, :etag, :checksum, :indexed_at)
                        """
                    ),
                    {
                        "id": document_id,
                        "domain": domain,
                        "repository": repository,
                        "object_key": object_key,
                        "etag": etag,
                        "checksum": checksum,
                        "indexed_at": datetime.now(UTC),
                    },
                )
            for number, (chunk, embedding) in enumerate(zip(content, embeddings, strict=True)):
                session.execute(
                    text(
                        """
                        INSERT INTO rag_chunks (document_id, chunk_number, content, embedding)
                        VALUES (:document_id, :chunk_number, :content, CAST(:embedding AS vector))
                        """
                    ),
                    {
                        "document_id": document_id,
                        "chunk_number": number,
                        "content": chunk,
                        "embedding": json.dumps(embedding, separators=(",", ":")),
                    },
                )

    def delete_missing(self, domain: str, repository: str, prefix: str, keys: set[str]) -> None:
        with self.database.sessions.begin() as session:
            rows = session.execute(
                text(
                    """
                    SELECT id, object_key
                    FROM rag_documents
                    WHERE domain_name = :domain AND repository = :repository
                      AND object_key LIKE :prefix
                    """
                ),
                {
                    "domain": domain,
                    "repository": repository,
                    "prefix": prefix.rstrip("/") + "/%",
                },
            ).mappings()
            for row in rows:
                if row["object_key"] not in keys:
                    session.execute(text("DELETE FROM rag_documents WHERE id = :id"), {"id": row["id"]})

    def search(
        self,
        domain: str,
        repository: str,
        query_embedding: list[float],
        query: str,
        limit: int,
    ) -> list[dict]:
        with self.database.sessions() as session:
            rows = session.execute(
                text(
                    """
                    SELECT c.content, d.object_key,
                           1 - (c.embedding <=> CAST(:embedding AS vector)) AS semantic_score,
                           ts_rank_cd(c.search_vector, websearch_to_tsquery('simple', :query)) AS text_score
                    FROM rag_chunks c
                    JOIN rag_documents d ON d.id = c.document_id
                    WHERE d.domain_name = :domain
                      AND (d.repository = '' OR d.repository = :repository)
                    ORDER BY
                        (1 - (c.embedding <=> CAST(:embedding AS vector))) * 0.7
                        + ts_rank_cd(c.search_vector, websearch_to_tsquery('simple', :query)) * 0.3 DESC
                    LIMIT :limit
                    """
                ),
                {
                    "domain": domain,
                    "repository": repository,
                    "embedding": json.dumps(query_embedding, separators=(",", ":")),
                    "query": query,
                    "limit": limit,
                },
            ).mappings()
            return [dict(row) for row in rows]

    def delete_unconfigured_sources(self, sources: list[tuple[str, str, str]]) -> None:
        """Retire documents whose domain, repository, or source prefix was removed."""
        with self.database.sessions.begin() as session:
            rows = (
                session.execute(text("SELECT id, domain_name, repository, object_key FROM rag_documents"))
                .mappings()
                .all()
            )
            for row in rows:
                configured = any(
                    row["domain_name"] == domain
                    and row["repository"] == repository
                    and row["object_key"].startswith(prefix.strip("/") + "/")
                    for domain, repository, prefix in sources
                )
                if not configured:
                    session.execute(text("DELETE FROM rag_documents WHERE id = :id"), {"id": row["id"]})
