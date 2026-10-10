# Hive architecture and module boundaries

Repository: `hive`. Scope: agent platform responsibilities and package structure.

## Modules

`hive/` is the control plane: FastAPI backend, served React UI, database persistence, monitoring
ingestion, agent state/health, review scheduling, RAG retrieval, and execution of agent decisions.
`sre/` investigates incidents and proposes repository fixes or manual verification actions.
`pr_review/` reviews PR revisions and returns assessments and merge decisions.
`packages/core/` contains shared domain enums, messaging contracts/transport, prompt access,
audit models, and common integrations used by multiple modules.

Python applications follow `<module>/src/<import_package>/`; `pr_review` is the import spelling
for the `pr-review` domain. Shared contracts belong in core; single-domain business rules stay
with their owner. Hive's `domains/sre/` and `domains/pr_review/` isolate orchestration and
execution for each domain. Worker `application/`, `domain/`, `integrations/`, and `tools/`
separate workflow, models, adapters, and native LangChain tools.

## Decision versus execution

Workers synchronize/check out repositories and collect the evidence needed for decisions.
Hive creates branches/PRs, performs approved merges/manual actions, persists records, and sends
Discord notifications. Workers do not connect to the application database, manage status
records, or expose operational APIs. The HTTP server on a worker exists for health/readiness.

Hive owns the database `agent` table. The persisted active boolean controls dispatch; public
status strings describe active, idle, or down after health observation. Idle and down are not
synonyms. Default agent registration is idle. Agent domain, rather than a historical bot name,
is the routing identity in configuration, events, and UI requests.

## Runtime and interfaces

Startup loads YAML/settings and constructs owned clients; shutdown closes them. Hive builds
domain runtimes for configured domains, with repositories/services appropriate to each domain.
The UI talks to Hive, not directly to workers. Worker health checks use internal Service URLs.
The same Hive image serves built UI files and backend endpoints; UI runtime configuration
avoids embedding environment-specific API URLs in a separate frontend release.

Sources: `hive/src/hive/bootstrap/`, `hive/src/hive/domains/`,
`hive/src/hive/application/agent_service.py`, `hive/src/hive/server.py`,
`hive/ui/src/`, `sre/src/sre/`, `pr_review/src/pr_review/`, `packages/core/src/core/`.
