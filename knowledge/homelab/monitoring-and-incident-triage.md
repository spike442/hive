# Homelab monitoring and incident triage

Repository: `homelab`. Scope: alert origin, routing, and evidence collection.

## Monitoring responsibilities

Prometheus evaluates metric rules; Alertmanager groups and inhibits notifications. Gatus checks
application endpoints and submits alerts to Alertmanager's API. Its sidecar discovers supported
Service/HTTPRoute annotations, so not every endpoint is handwritten in the base Gatus config.
Grafana displays data. Fluent Bit ships logs to VictoriaLogs. Flux notifications are a separate
controller-event path; they are not the same as Prometheus alert evaluation.

Alertmanager's configured event recorder publishes JSON to `hive.alerts`. Its ordinary receiver
is configured as null; this pipeline should not be described as a direct Discord webhook.
Hive ingests alerts, dispatches investigations when active, stores decisions, and sends Discord
notifications. Gatus-origin labels let Hive distinguish endpoint alerts after Alertmanager
normalization. A configured `send-on-resolved` flag alone does not prove the downstream payload
has the expected resolved status: inspect the actual recorded event if recovery is not reflected.

## Targeted investigation

Begin with alert identity, labels, annotations, start/end times, status, and query when available.
For a workload failure, inspect its controller, conditions, recent events, relevant container
logs, dependencies, and owning Git declaration. For an endpoint failure, compare in-cluster
Service health with DNS/Gateway behavior. For backups, compare schedule, last success, policy,
repository, and mover evidence. Query only the metrics or resources needed for the hypothesis.

Do not ship the entire cluster state to an LLM or call a resource healthy because its Pod exists.
Separate missing configuration, bad desired state, stale Flux revision, and live dependency
failure. Evidence should identify the layer that fails and the smallest corrective declaration.

## Delivery and resolution diagnosis

If an alert is missing, trace metric/rule or Gatus detection, Alertmanager active alerts/event
recording, Kafka topic, Hive consumer and persisted incident, Temporal workflow history, agent
active state, task-queue activity execution, stored decision, then Discord delivery. Idle SRE
workflows wait durably and continue after activation. Notification failure is different from
investigation failure.

Hive marks matching incidents resolved when an incoming alert says resolved, even while idle.
A created or merged PR does not resolve an incident by itself. Preserve the fingerprint and
source across firing and recovery events so they match the same incident.

Sources: `kubernetes/apps/observability/kube-prometheus-stack/app/alertmanager-secret.yaml`,
`kubernetes/apps/observability/gatus/app/resources/config.yaml`,
`kubernetes/apps/observability/gatus/app/helmrelease.yaml`,
`kubernetes/components/alerts/`, `kubernetes/apps/observability/fluent-bit/`,
`kubernetes/apps/observability/victoria-logs/`.
