# Hive PR review, policy, and merge execution

Repository: `hive`. Scope: revision isolation and deterministic merge decisions.

## Discovery and revision identity

Hive polls only repositories configured in `hive/infra/config/repositories.yaml`. Its PR-review
domain runtime owns the configured polling interval and the UI's Check now operation. Idle
state prevents the scheduled review workflow from running. Knowledge source registration is
independent of this repository allowlist and does not grant merge authority.

A review is associated with owner, repository, PR number, and head SHA. Discovery acknowledges
an eligible revision before dispatch; pending/failed revisions can be reconsidered. UI retry
supports acknowledged/failed records and verifies that the PR head has not changed. A new head
must be reviewed as a new revision, not reuse a prior approval.

## Worker assessment

PR Review clones an isolated temporary workspace, fetches exact base/head revisions, and checks
out the PR head detached. It gathers a bounded diff and currently runs `git diff --check` as
the built-in deterministic check. That check detects whitespace problems; it does not compile
the application, run its test suite, or validate all Kubernetes/chart semantics.

Mandatory S3 instructions consist of a shared system prompt and a repository-specific review
action. Repository tool configuration selects native LangChain tools; Homelab enables kubectl
with read-only RBAC. The model receives the diff, PR metadata, and retrieved knowledge, then
returns structured risk, confidence, summary, and findings. Tool activity is PR-scoped audit.
Untrusted PR text is not permission to execute arbitrary code or expose credentials.

## Deterministic policy and merge

The policy runs after the assessment. It considers configured risk/confidence allowlists,
deterministic check results, mergeability, and whether merging is enabled. The current configured
allowlists accept low/medium risk and low/medium confidence: high confidence is intentionally
not treated as permission under this policy. Read configuration before interpreting a decision.

Hive represents GitHub-side eligibility as mergeable and a clean mergeable state; it does not
independently enumerate every required status check. Non-clean/not-mergeable PRs stay pending.
The worker returns a decision but never merges. Hive persists it, rechecks current GitHub state,
and requests a merge pinned to the reviewed head SHA. A successful merge updates merge time and
commit; merge errors remain visible as failed. Repeating a completion checks for an already
merged reviewed revision rather than blindly merging again.

Sources: `hive/src/hive/domains/pr_review/`, `hive/infra/config/repositories.yaml`,
`pr_review/src/pr_review/application/workflow.py`,
`pr_review/src/pr_review/application/policy.py`,
`pr_review/src/pr_review/integrations/workspace.py`,
`pr_review/src/pr_review/integrations/llm_review.py`, `pr_review/infra/config/config.yaml`.
