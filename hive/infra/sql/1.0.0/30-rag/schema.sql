-- The CloudNativePG Database resource owns the vector extension.

DROP TABLE IF EXISTS rag_chunks;
DROP TABLE IF EXISTS rag_documents;

CREATE TABLE rag_documents (
    id UUID PRIMARY KEY,
    domain_name TEXT NOT NULL,
    repository TEXT NOT NULL,
    object_key TEXT NOT NULL,
    source_etag TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    indexed_at TIMESTAMPTZ NOT NULL,
    UNIQUE (domain_name, repository, object_key)
);

CREATE TABLE rag_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
    chunk_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', content)
    ) STORED,
    UNIQUE (document_id, chunk_number)
);

CREATE INDEX rag_chunks_embedding_idx
    ON rag_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX rag_chunks_search_idx ON rag_chunks USING gin (search_vector);
CREATE INDEX rag_documents_scope_idx ON rag_documents (domain_name, repository);

GRANT USAGE ON SCHEMA public TO hive;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE rag_documents, rag_chunks TO hive;
GRANT USAGE, SELECT ON SEQUENCE rag_chunks_id_seq TO hive;
