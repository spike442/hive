# Hive UI and operator action semantics

Repository: `hive`. Scope: management UI, refresh, and interpreting displayed records.

## Data and navigation

Hive serves the built React/TypeScript UI and its backend in one deployment. The default Hive
dashboard summarizes the platform; domain views expose SRE incidents and PR-review records.
Runtime configuration identifies the Hive API, and the displayed release version comes from
the backend rather than a separately hardcoded frontend version. Agent health/state comes from
Hive, not from an incident's or review's status.

Hooks poll backend resources and support a manual refresh trigger. They are not a Kafka
subscription or server-pushed live stream. Empty filter results must remain distinguishable
from request failures; neither proves there are no records in the database. API list limits
mean displayed counts summarize the loaded records, not an unlimited database aggregate.

Incident views filter by source/status and search text. Ignored incidents are excluded from
the default all view but available through their status filter. Resolved incidents are still
records and are not deleted because a PR merged. Review views have their own status filters,
checks, assessment, merge decision, and PR links.

## Operator controls

Agent toggles update Hive's persisted state. Idle stops ordinary dispatch/scheduling; it is not
an emergency cancellation of an already-running command or a request to scale a Deployment.
Health observations can show down independently of the stored active flag.

Incident replay submits operator guidance for another run, using stored incident history.
Manual-action approval executes a specific proposed command through Hive; inspect the command
before approving, because the executor runs a shell and approval is a real external action.
Ignore changes tracking state. Delete removes a record; it does not resolve the upstream alert
or undo a PR. Review Check now triggers discovery; Retry is revision-scoped and only accepts
eligible acknowledged/failed records. Deleting a review does not close or revert its GitHub PR.

Mutating API routes require control authorization. UI disable states improve interaction but
are not a security boundary. Diagnose authorization, idle state, stale head SHA, schema errors,
and network failures from the backend response rather than assuming a button silently succeeded.

Sources: `hive/ui/src/main.tsx`, `hive/ui/src/hooks/`, `hive/ui/src/api/`,
`hive/ui/src/components/`, `hive/src/hive/web/api.py`, `hive/src/hive/web/auth.py`,
`hive/src/hive/domains/sre/api.py`, `hive/src/hive/domains/pr_review/api.py`.
