# Hive SRE incident investigation and execution

Repository: `hive`. Scope: alert acknowledgment, diagnosis, replay, and resolution.

## Receive and investigate

Hive receives normalized monitoring events over Kafka. Incident identity uses the alert
fingerprint; source, labels, annotations, status, and timestamps remain alert data. Hive persists
firing alerts and starts a durable Temporal workflow. If the SRE domain is idle, the workflow waits
and periodically checks whether the incident is still current; activating SRE allows it to proceed
without replaying the alert. Incoming resolved alerts still update a matching incident, and the
workflow stops before investigation if it is no longer current. Ignored incidents are an explicit
operator choice, not a successful repair.

When dispatched, the SRE worker synchronizes the public repository and starts from the alert rather than a
whole-cluster dump. The LangChain agent uses selected native tools for bounded shell inspection,
Prometheus queries, and GitHub reads. System/action prompts specify behavior; Hive-supplied RAG
excerpts supply reference facts. The shell policy and Kubernetes service account constrain what
the worker can inspect. Do not assume the worker has permission to mutate resources.

The diagnosis includes evidence, proposed changes or manual actions, risk/confidence, verification,
and rollback where applicable. A plausible hypothesis without an actionable supported fix is
not a completed repair. SRE returns the decision; Hive owns execution.

## Apply a fix or request verification

Hive's IncidentService validates a proposed diagnosis before applying file changes. Complete
proposals require evidence, validation, rollback, and secret-safe content. Changes are grouped
into one PR for the fix, even if several files change. Hive uses its checkout and SSH identity
to push the branch, then its GitHub API integration to create the PR and risk/confidence labels.
Existing-PR lookup helps avoid duplicate creation on repeated completion events.

Without a valid repository fix, the incident remains blocked. A diagnosis may instead offer
manual actions for operator approval. Hive executes the selected approved command with bounded
time/output and persists its result; a successful manual action moves the incident to pending,
not automatically resolved. Current RBAC still applies. Approval is not a bypass for the rule
that infrastructure changes go through GitOps.

## Replay and close

An operator can replay eligible incidents with new guidance. Stored incident history and replay
prompts accompany the command; SRE assembles the relevant prior history inside its workflow.
This is explicit replay context, not hidden cross-incident LLM memory. Replays must not inherit
another incident's response chain or obsolete approval controls.

Statuses distinguish acknowledged, processing, pending, failed, blocked, PR-created, ignored,
and resolved. Only matching monitoring resolution closes the incident. Neither PR creation,
PR merge, an agent confidence score, nor a successful verification command proves resolution.

Sources: `hive/src/hive/domains/sre/`, `sre/src/sre/application/`,
`sre/src/sre/integrations/llm_diagnosis.py`, `sre/src/sre/tools/`,
`packages/core/src/core/domain/enums.py`, `hive/ui/src/components/IncidentViews.tsx`.
