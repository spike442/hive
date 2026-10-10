# Hive orchestration, delivery, and audit

Repository: `hive`. Scope: Kafka ingress, Temporal workflows, and persistence boundaries.

## Message and work flow

Alertmanager publishes normalized alert events to `hive.alerts`. Hive is the only Kafka
consumer: it validates an alert, persists its incident receipt, and starts an SRE workflow in
Temporal. Kafka is not the internal agent command/result bus. Hive starts the PR-review poll
workflow from a Temporal Schedule or the UI; the poll workflow discovers configured PRs and
starts one workflow per revision. Hive owns workflow activities that read/write its database,
check agent active state, retrieve RAG context, and apply merge or approved-action decisions.
SRE and PR Review workers run domain-specific activities on their own Temporal task queues.

Temporal workflow history is the durable orchestration record. Hive's PostgreSQL tables remain
the source of truth for UI state, incident/review status, and stored audit actions. Kafka topic
retention and offsets are ingress delivery controls, not business history. Workflow/activity
names and task queues are contracts; update Hive and its workers together.

## Delivery and retry

Hive commits a Kafka alert only after it has persisted the incident and started or identified its
Temporal workflow. The database and Temporal are not one distributed transaction: if either
service is unavailable, Hive retries the Kafka message and uses incident/workflow identity to
avoid creating duplicate work. Temporal retries activities according to their retry policy.
Database transitions and external GitHub operations are guarded where possible, but no system
can make a shell command or GitHub merge atomic with a PostgreSQL commit. Manual shell actions
therefore use one activity attempt; after an interrupted action, inspect its recorded outcome
before running it again.

Kafka sends invalid messages to `hive.dead-letter`; transient processing failures are retried
without committing the source offset. Temporal retains workflow history per its configured
retention. UI replay/retry starts new workflows with explicit correlation to the incident or PR;
it does not reuse another incident's LLM response chain.

## Audit ownership

Agents return timestamped tool/audit actions with their decision. Hive stores those actions with
the incident or PR review. Temporal history records orchestration and activity outcomes, not
every token or every internal LLM step. An external side effect can succeed while its activity
completion is lost; inspect GitHub state and the stored run before repeating it. Bound outputs
and keep credentials out of commands and audit payloads.

Sources: `packages/core/src/core/messaging/`, `packages/core/src/core/orchestration.py`,
`hive/src/hive/orchestration/`, `hive/src/hive/domains/`, `hive/src/hive/persistence/`,
`sre/src/sre/worker.py`, `pr_review/src/pr_review/worker.py`.
