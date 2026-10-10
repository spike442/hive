export const INCIDENT_STATUS = {
  ACKNOWLEDGED: "acknowledged",
  PENDING: "pending",
  PROCESSING: "processing",
  FAILED: "failed",
  BLOCKED: "blocked",
  PR_CREATED: "pr_created",
  IGNORED: "ignored",
  RESOLVED: "resolved",
} as const;
export type IncidentStatus =
  (typeof INCIDENT_STATUS)[keyof typeof INCIDENT_STATUS];

export const AGENT_STATUS = {
  ACTIVE: "active",
  IDLE: "idle",
  DOWN: "down",
} as const;
export type AgentStatus = (typeof AGENT_STATUS)[keyof typeof AGENT_STATUS];

export const REVIEW_STATUS = {
  ACKNOWLEDGED: "acknowledged",
  PENDING: "pending",
  PROCESSING: "processing",
  DECIDED: "decided",
  FAILED: "failed",
  MERGED: "merged",
} as const;
export type ReviewStatus = (typeof REVIEW_STATUS)[keyof typeof REVIEW_STATUS];

export const INCIDENT_EVENT = {
  ACKNOWLEDGED: "acknowledged",
  CREATED: "created",
  REOPENED: "reopened",
  REPLAYED: "replayed",
  PROCESSING: "processing",
  PENDING: "pending",
  FAILED: "failed",
  BLOCKED: "blocked",
  PR_CREATED: "pr_created",
  RESOLVED: "resolved",
  IGNORED: "ignored",
  MANUAL_ACTION_EXECUTED: "manual_action_executed",
} as const;
export type IncidentEvent =
  (typeof INCIDENT_EVENT)[keyof typeof INCIDENT_EVENT];

export const DIAGNOSIS_STATUS = { OBSERVED: "observed" } as const;
export const REPLAYABLE_INCIDENT_STATUSES = new Set<IncidentStatus>([
  INCIDENT_STATUS.ACKNOWLEDGED,
  INCIDENT_STATUS.FAILED,
  INCIDENT_STATUS.BLOCKED,
]);
export const CLOSED_INCIDENT_STATUSES = new Set<IncidentStatus>([
  INCIDENT_STATUS.RESOLVED,
  INCIDENT_STATUS.IGNORED,
]);

export type Panel = "Overview" | "Incidents" | "Activity";
export type ManualAction = {
  title: string;
  command: string;
  reason: string;
  validation: string;
};
export type DiagnosisSnapshot = {
  incident?: string;
  hypothesis?: string;
  status?: string;
  confidence?: "low" | "medium" | "high";
  risk?: "low" | "medium" | "high" | "critical";
  manual_actions?: ManualAction[];
};
export type TimelineEvent = {
  at: string;
  event: string;
  prompt?: string;
  diagnosis?: DiagnosisSnapshot;
};
export type AgentActivity = { at: string; status: AgentStatus; domain: string };
export type ManagedAgent = {
  domain: "sre" | "pr-review";
  status: AgentStatus;
  version: string;
  healthy: boolean;
};
export type UiConfig = { hive_url: string };
export type PullRequestReview = {
  id: number;
  repository: string;
  pull_request_number: number;
  pull_request_url: string;
  status: ReviewStatus;
  risk?: string | null;
  confidence?: string | null;
  summary: string;
  updated_at: string;
  merged_at?: string | null;
  merge_commit_sha?: string;
  review_actions?: Array<{ action: string; details: Record<string, unknown> }>;
};
export type DiagnosisHistory = {
  at: string;
  diagnosis: {
    incident?: string;
    hypothesis?: string;
    status?: string;
    confidence?: Incident["confidence"];
    risk?: Incident["risk"];
    manual_actions?: ManualAction[];
  };
};
export type Incident = {
  id: string;
  title: string;
  summary: string;
  source: string;
  alertname: string;
  alertStatus: string;
  startsAt: string;
  pullRequestUrl: string;
  status: IncidentStatus;
  severity: string;
  namespace: string;
  pod: string;
  confidence: "low" | "medium" | "high";
  risk: "low" | "medium" | "high" | "critical";
  updated: string;
  replayedAt: string | null;
  replayPrompts: string[];
  manualActions: ManualAction[];
  manualActionHistory: Array<Record<string, unknown>>;
  diagnosisHistory: DiagnosisHistory[];
  timeline: TimelineEvent[];
  evidence: string[];
  files: string[];
  actions: string[];
};

export type ApiIncident = {
  id: string;
  status: IncidentStatus;
  alert: {
    source?: string;
    status?: string;
    startsAt?: string;
    endsAt?: string;
    generatorURL?: string;
    labels?: Record<string, string>;
    annotations?: Record<string, string>;
  };
  diagnosis: {
    incident?: string;
    confidence?: Incident["confidence"];
    risk?: Incident["risk"];
    evidence?: string[];
    proposed_files?: string[];
    manual_actions?: ManualAction[];
  };
  pull_request_url?: string | null;
  updated_at?: string;
  replayed_at?: string | null;
  replay_prompts?: string[];
  manual_actions?: Array<Record<string, unknown>>;
  diagnosis_history?: DiagnosisHistory[];
  timeline?: TimelineEvent[];
};

export const statusFilters: IncidentStatus[] = [
  INCIDENT_STATUS.ACKNOWLEDGED,
  INCIDENT_STATUS.PENDING,
  INCIDENT_STATUS.PROCESSING,
  INCIDENT_STATUS.FAILED,
  INCIDENT_STATUS.BLOCKED,
  INCIDENT_STATUS.PR_CREATED,
  INCIDENT_STATUS.IGNORED,
  INCIDENT_STATUS.RESOLVED,
];

export function toIncident(item: ApiIncident): Incident {
  const annotations = item.alert.annotations ?? {};
  return {
    id: item.id,
    title: annotations.summary ?? item.diagnosis.incident ?? item.id,
    summary: annotations.description ?? "No incident description recorded.",
    source: item.alert.source ?? item.alert.labels?.source ?? "unknown",
    alertname: item.alert.labels?.alertname ?? "unknown",
    alertStatus: item.alert.status ?? "unknown",
    startsAt: item.alert.startsAt ?? "unknown",
    pullRequestUrl: item.pull_request_url ?? "",
    status: item.status,
    severity: item.alert.labels?.severity ?? "unknown",
    namespace: item.alert.labels?.namespace ?? "",
    pod: item.alert.labels?.pod ?? "",
    confidence: item.diagnosis.confidence ?? "low",
    risk: item.diagnosis.risk ?? "low",
    updated: item.updated_at ?? "",
    replayedAt: item.replayed_at ?? null,
    replayPrompts: item.replay_prompts ?? [],
    manualActions: item.diagnosis.manual_actions ?? [],
    manualActionHistory: item.manual_actions ?? [],
    diagnosisHistory: item.diagnosis_history ?? [],
    timeline: item.timeline ?? [],
    evidence: item.diagnosis.evidence ?? [],
    files: item.diagnosis.proposed_files ?? [],
    actions: [
      ...(item.pull_request_url ? ["open-pr"] : []),
      ...(REPLAYABLE_INCIDENT_STATUSES.has(item.status) ? ["replay"] : []),
      ...(CLOSED_INCIDENT_STATUSES.has(item.status) ? [] : ["ignore"]),
      "delete",
    ],
  };
}
