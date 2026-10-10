# Hive configuration, releases, and operational diagnosis

Repository: `hive`. Scope: startup prerequisites and safe delivery.

## Configuration and credentials

Each module keeps non-secret YAML in `infra/config/`, loaded with pydantic-settings. External
Secrets inject environment credentials. Hive owns database, GitHub App, SSH push, Discord, Kafka
Alertmanager ingress, Temporal orchestration, and retrieval credentials. SRE and PR Review own
their model and prompt-store credentials and connect to Temporal; they do not use Kafka.
Do not copy one application's vault item into another as a shortcut. Exact field names belong
in current settings classes, ExternalSecrets, and `infra/SETUP.md`, not in long-lived examples.

S3 mandatory prompts have no local-context fallback. Missing credentials/objects fail startup
or the relevant action. SRE validates its system prompt checksum and caches startup prompts;
PR Review can check prompt ETags through its PromptStore. Do not confuse prompt refresh with
knowledge indexing: they have different storage prefixes and lifecycles.

HOME, KUBECONFIG, mounted service-account material, SSH configuration, known_hosts, and private
key permissions belong in the container/deployment environment. A read-only kubeconfig grants
only its service account's actual RBAC. Workers use internal cluster Services, not public ingress.

## Build and release

The root CI/publish workflows dispatch module workflows. Shared Python build/test machinery
lives in a composite action. Quality reporting has its own workflow and artifacts; inspect
actual job outcomes rather than inferring quality from image publication. Python project
versions come from each module's pyproject.toml; publication creates module-specific Git tags
and versioned images. An existing release tag is not silently moved to a different commit.

Hive's Docker build includes the UI build and serves it from the backend. Worker images include
only their own code and shared core dependencies, not the UI. Shared CLI installation is in
root `scripts/install-tools.sh`. CLI tool availability and Python dependency installation are
separate prerequisites. Root Taskfile coordinates setup, S3 upload, schema apply, and RAG indexing.

## Diagnose by failure layer

Startup: check Secret delivery, YAML validation, prompt object/checksum, model connectivity,
database schema/extension, Temporal frontend/namespace, and (for Hive) Kafka authentication/topic
existence. Worker /healthz reflects its Temporal worker. Hive health/version and UI configuration
must also be reachable.

Missing work: trace monitoring or GitHub discovery, persisted acknowledgment, Temporal workflow
history, active state, task-queue activity execution, stored decision, and notification. A blocked
diagnosis is different from a transport error. An SSH push failure is different from GitHub API
authentication. A UI error can be backend schema/configuration failure, not missing frontend assets.

Rollout: publish the chosen module image, change its Homelab declaration, and let Flux reconcile.
Do not apply schema resets, upload S3 files, trigger work, or mutate cluster state merely while
reviewing documentation. Never log settings objects or decrypted secret values.

Sources: `.github/workflows/`, `.github/actions/`, `scripts/install-tools.sh`, `Taskfile.yml`,
`hive/Dockerfile`, `sre/Dockerfile`, `pr_review/Dockerfile`,
`sre/src/sre/infrastructure/config.py`, `pr_review/src/pr_review/infrastructure/config.py`,
`hive/src/hive/infrastructure/config.py`, `infra/SETUP.md`.
