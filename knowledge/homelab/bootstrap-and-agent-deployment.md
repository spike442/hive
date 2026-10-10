# Homelab bootstrap and agent deployment dependencies

Repository: `homelab`. Scope: host/bootstrap boundaries and Hive rollout prerequisites.

## Host preparation versus reconciliation

Ansible inventory/group variables describe machines and K3s settings. OS roles configure host
packages, filesystems, networking, time, firewall, and SSH. Kubernetes playbooks prepare/install
K3s. Bootstrap Helmfile and resources establish controllers required before Flux can reconcile
the application tree. These privileged installation operations are operator workflows, not
incident-remediation tools for an LLM.

Pi-hole has a separate Ansible role and Docker Compose lifecycle on the NAS. A failure there
is not repaired by restarting a similarly named Kubernetes integration. Avoid commands that
print decrypted credentials or reset passwords into logs.

## Agent application layout

Hive, SRE, and PR Review are dedicated apps in the `agents` namespace. Each has its own
`ks.yaml` and `app/`. Hive additionally owns its application `database/` and Kafka ingress user
and topics. Temporal is a shared messaging-platform app under `kubernetes/apps/messaging/temporal/`.
Flux dependencies connect prerequisite Kustomizations to the application; keep setup with its
owner rather than introducing separate platform applications for app-specific credentials.

Hive's main app serves both backend and built UI. Workers expose internal health endpoints and
consume Temporal task queues; they do not expose operational HTTP routes or use Kafka. Service accounts,
ClusterRoles, projected tokens, kubeconfig mounts, HOME, and SSH mounts are deployment concerns.
Both worker roles are read-only; neither permission set should be called cluster-admin.

## Rollout proof

Before rollout, verify required CRDs/operators, SecretStore health, database/extension/schema,
Temporal databases/role/secret/chart, Hive Kafka ingress topics/user/ACLs, prompt objects/checksum,
embedding credentials if RAG is enabled, and
image tags. Database creation is not schema initialization. Prompt upload is not knowledge
indexing. Image publication is not Flux deployment.

After GitOps reconciliation, check dependency conditions, Deployment rollout, pod events,
startup logs, Temporal frontend/worker readiness, Hive Kafka ingress, Hive's health/version response, idle state in the database,
and UI API access. Test one real event before broad replay. A database idle flag is not a
replica count, and idle is not process-down. Current image versions and replicas must be read
from manifests, not this document.

Sources: `ansible/playbooks/kubernetes/`, `ansible/roles/os/`, `ansible/roles/pihole/`,
`bootstrap/helmfile.d/`, `kubernetes/apps/agents/hive/ks.yaml`,
`kubernetes/apps/agents/sre/ks.yaml`, `kubernetes/apps/agents/pr-review/ks.yaml`,
`kubernetes/apps/agents/sre/app/clusterrole.yaml`,
`kubernetes/apps/agents/pr-review/app/clusterrole.yaml`.
