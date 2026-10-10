import { useMemo } from "react";
import { BarChart3 } from "lucide-react";
import { activityBuckets } from "../format";
import {
  CLOSED_INCIDENT_STATUSES,
  INCIDENT_STATUS,
  statusFilters,
  type AgentActivity,
  type AgentStatus,
  type Incident,
  type IncidentStatus,
  type PullRequestReview,
  type ManagedAgent,
} from "../model";
import { StatusIcon } from "./StatusIcon";

function ActivityGraph({
  timestamps,
  label,
}: {
  timestamps: string[];
  label: string;
}) {
  const values = useMemo(() => {
    return activityBuckets(timestamps, Date.now());
  }, [timestamps]);
  const maximum = Math.max(1, ...values);
  return (
    <div className="activity-chart" aria-label={label}>
      <div className="activity-chart-heading">
        <span>{label}</span>
        <BarChart3 size={15} />
      </div>
      <div className="activity-bars">
        {values.map((value, index) => (
          <i
            key={index}
            style={{ height: `${Math.max(8, (value / maximum) * 100)}%` }}
            title={`${value} event${value === 1 ? "" : "s"}`}
          />
        ))}
      </div>
      <div className="activity-chart-axis">
        <span>11h ago</span>
        <span>now</span>
      </div>
    </div>
  );
}

export function OverviewPanel({
  incidents,
  agentStatus,
  agentEvents,
  domain,
}: {
  incidents: Incident[];
  agentStatus: AgentStatus;
  agentEvents: AgentActivity[];
  domain: string;
}) {
  const counts = useMemo(
    () =>
      Object.fromEntries(
        statusFilters.map((status) => [
          status,
          incidents.filter((incident) => incident.status === status).length,
        ]),
      ),
    [incidents],
  );
  const sources = useMemo(
    () =>
      Array.from(new Set(incidents.map((incident) => incident.source)))
        .sort()
        .map((source) => ({
          source,
          count: incidents.filter((incident) => incident.source === source)
            .length,
        })),
    [incidents],
  );
  const open = incidents.filter(
    (incident) => !CLOSED_INCIDENT_STATUSES.has(incident.status),
  ).length;
  const statusLabels: Record<IncidentStatus, string> = {
    [INCIDENT_STATUS.ACKNOWLEDGED]: "Acknowledged",
    [INCIDENT_STATUS.PENDING]: "Pending",
    [INCIDENT_STATUS.PROCESSING]: "Processing",
    [INCIDENT_STATUS.FAILED]: "Failed",
    [INCIDENT_STATUS.BLOCKED]: "Blocked",
    [INCIDENT_STATUS.PR_CREATED]: "PR created",
    [INCIDENT_STATUS.IGNORED]: "Ignored",
    [INCIDENT_STATUS.RESOLVED]: "Resolved",
  };
  const timestamps = [
    ...agentEvents.map((event) => event.at),
    ...incidents.flatMap((incident) => [
      ...incident.timeline.map((event) => event.at),
      ...incident.manualActionHistory.map((event) => String(event.at ?? "")),
    ]),
  ];
  return (
    <section
      className="overview-panel console-panel"
      aria-label="Agent dashboard"
    >
      <div className="agent-dashboard-header">
        <div>
          <span className="eyebrow">AGENT DASHBOARD</span>
          <h2>{domain}</h2>
        </div>
        <strong className={`agent-status-readout ${agentStatus}`}>
          <span /> {agentStatus}
        </strong>
      </div>
      <div className="overview-summary">
        <div>
          <strong>{incidents.length}</strong>
          <span>Total incidents</span>
        </div>
        <div>
          <strong>{open}</strong>
          <span>Open</span>
        </div>
        <div>
          <strong>{counts.resolved}</strong>
          <span>Resolved</span>
        </div>
      </div>
      <ActivityGraph
        timestamps={timestamps}
        label="Agent activity · last 12 hours"
      />
      <div className="overview-sections">
        <div className="overview-section">
          <div className="overview-section-title">Status</div>
          <div className="overview-count-grid">
            {statusFilters.map((status) => (
              <div className={`overview-count ${status}`} key={status}>
                <StatusIcon status={status} />
                <span>{statusLabels[status]}</span>
                <strong>{counts[status]}</strong>
              </div>
            ))}
          </div>
        </div>
        <div className="overview-section">
          <div className="overview-section-title">Sources</div>
          <div className="overview-source-list">
            {sources.length === 0 ? (
              <span className="overview-empty">No sources yet</span>
            ) : (
              sources.map(({ source, count }) => (
                <div className="overview-source" key={source}>
                  <span>{source}</span>
                  <strong>{count}</strong>
                  <i>
                    <b
                      style={{
                        width: `${Math.max(8, Math.round((count / Math.max(1, incidents.length)) * 100))}%`,
                      }}
                    />
                  </i>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

export function HiveDashboard({
  version,
  agents,
  incidents,
  agentEvents,
  reviews,
  onSelectAgent,
}: {
  version: string;
  agents: ManagedAgent[];
  incidents: Incident[];
  agentEvents: AgentActivity[];
  reviews: PullRequestReview[];
  onSelectAgent: (agent: string) => void;
}) {
  const timestamps = [
    ...agentEvents.map((event) => event.at),
    ...reviews.map((review) => review.updated_at),
    ...incidents.flatMap((incident) =>
      incident.timeline.map((event) => event.at),
    ),
  ];
  const activeIncidents = incidents.filter(
    (incident) => !CLOSED_INCIDENT_STATUSES.has(incident.status),
  ).length;
  return (
    <section
      className="hive-dashboard console-panel"
      aria-label="Hive dashboard"
    >
      <div className="hive-dashboard-header">
        <div>
          <span className="eyebrow">HIVE CONTROL TOWER</span>
          <h2>Agent overview</h2>
          <p>Monitor the platform and open an agent workspace.</p>
        </div>
        <span className="hive-version">v{version}</span>
      </div>
      <div className="hive-agent-grid">
        {agents.map((agent) => (
          <button
            className="hive-agent-card"
            key={agent.domain}
            onClick={() => onSelectAgent(agent.domain)}
          >
            <img src={`/${agent.domain}.png`} alt="" />
            <span>
              <strong>{agent.domain}</strong>
              <small>{agent.domain.replaceAll("_", " ")}</small>
            </span>
            <b className={agent.status}>
              <i />
              {agent.status}
            </b>
          </button>
        ))}
      </div>
      <div className="hive-summary">
        <div>
          <strong>{activeIncidents}</strong>
          <span>Active incidents</span>
        </div>
        <div>
          <strong>{reviews.length}</strong>
          <span>PR reviews</span>
        </div>
        <div>
          <strong>{incidents.length}</strong>
          <span>Total records</span>
        </div>
      </div>
      <ActivityGraph
        timestamps={timestamps}
        label="Hive activity · last 12 hours"
      />
    </section>
  );
}
