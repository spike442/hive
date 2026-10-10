# Hive persistence and retrieval-augmented generation

Repository: `hive`. Scope: data ownership, indexing, and grounded agent input.

## Database ownership and initialization

Only Hive connects to the shared PostgreSQL application database. SQLAlchemy repositories own
agent state, incoming events, incidents, reviews, and knowledge records. Workers receive typed
commands and return typed events instead of writing tables. The Hive account owns the schema.

SQL under `hive/infra/sql/<version>/` is split into ordered core, alert, review, and RAG domains.
These scripts drop and recreate tables: they are fresh-install scripts, not migrations. Running
them on an existing installation destroys the relevant records. CloudNativePG separately
provisions the database/role and vector extension. `task database:apply` uses psql and 1Password;
it is not a harmless application startup task.

## Knowledge indexing

The root `knowledge/` collection contains factual Markdown; mandatory prompts have separate S3
prefixes. Domain upload scripts copy the canonical collection to domain-specific knowledge
prefixes, using separate credentials. Hive's configured sources map each prefix to a domain
and repository. Indexing Hive/dotfiles does not add them to automated PR review.

`task rag:index` runs the indexer, not the workers. For each configured S3 source, it lists
objects, reads content, compares ETag/content checksum, and skips unchanged embeddings. Changed
documents are split around headings/paragraphs into overlapping bounded chunks, embedded, and
replaced transactionally. Missing objects and unconfigured sources are removed from the index.
The current source reader accepts objects under the prefix, so keep those prefixes Markdown-only.

`rag_documents` tracks domain, repository, object key, ETag/checksum, and indexing time.
`rag_chunks` stores text, chunk position, vector, and generated full-text data, linked with
cascading deletion. The schema fixes the vector dimension; changing embedding dimensions is
not merely changing YAML. Vector and text indexes support retrieval without a second database.

## Retrieval at dispatch

Hive embeds the alert/replay or PR query and searches within the request's domain/repository
(plus any explicitly repository-neutral records). Ranking combines cosine similarity and
full-text search with a bounded result count. It is not a cross-encoder reranker or a guaranteed
relevance threshold. Source references currently identify the object with a chunk marker, not
a precise source line. Workers receive only selected excerpts as `rag_context`.

RAG is reference lookup, not conversation memory or real-time cluster state. Prompts still need
to be sent to the LLM, and useful evidence may still require tools. Prompt cache keys can help
the provider reuse a repeated prefix; they do not eliminate input or establish an incident
session. Never elevate retrieved documents into system instructions.

Sources: `hive/src/hive/rag/`, `hive/src/hive/persistence/`,
`hive/infra/sql/`, `hive/infra/config/config.yaml`,
`packages/core/src/core/integrations/prompts.py`, `knowledge/README.md`.
