import {
  Activity,
  Archive,
  CheckCircle2,
  CircleDot,
  GitPullRequest,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { formatTimestamp, sortByTimestamp } from "../format";
import {
  AGENT_STATUS,
  INCIDENT_EVENT,
  type AgentActivity,
  type Incident,
} from "../model";

const activityIcons: Record<string, typeof Activity> = {
  [INCIDENT_EVENT.ACKNOWLEDGED]: CheckCircle2,
  [INCIDENT_EVENT.CREATED]: Activity,
  [INCIDENT_EVENT.REOPENED]: RefreshCw,
  [INCIDENT_EVENT.REPLAYED]: RefreshCw,
  [INCIDENT_EVENT.PROCESSING]: Activity,
  [INCIDENT_EVENT.PENDING]: CircleDot,
  [INCIDENT_EVENT.FAILED]: XCircle,
  [INCIDENT_EVENT.BLOCKED]: ShieldAlert,
  [INCIDENT_EVENT.PR_CREATED]: GitPullRequest,
  [INCIDENT_EVENT.RESOLVED]: CheckCircle2,
  [INCIDENT_EVENT.IGNORED]: Archive,
  [INCIDENT_EVENT.MANUAL_ACTION_EXECUTED]: ShieldAlert,
};

const activityLabels: Record<string, string> = {
  [INCIDENT_EVENT.ACKNOWLEDGED]: "acknowledged alert",
  [INCIDENT_EVENT.CREATED]: "received alert",
  [INCIDENT_EVENT.REOPENED]: "reopened incident",
  [INCIDENT_EVENT.REPLAYED]: "replayed investigation",
  [INCIDENT_EVENT.PROCESSING]: "started investigation",
  [INCIDENT_EVENT.PENDING]: "waiting for recovery",
  [INCIDENT_EVENT.FAILED]: "failed investigation",
  [INCIDENT_EVENT.BLOCKED]: "blocked for manual action",
  [INCIDENT_EVENT.PR_CREATED]: "created pull request",
  [INCIDENT_EVENT.RESOLVED]: "resolved incident",
  [INCIDENT_EVENT.IGNORED]: "ignored incident",
  [INCIDENT_EVENT.MANUAL_ACTION_EXECUTED]: "executed manual action",
};

export function ActivityFeed({
  incidents,
  agentEvents,
  domain,
}: {
  incidents: Incident[];
  agentEvents: AgentActivity[];
  domain: string;
}) {
  const incidentEvents = incidents.flatMap((incident) => {
    const timeline =
      incident.timeline.length > 0
        ? incident.timeline.map((entry) => ({
            at: entry.at,
            icon: activityIcons[entry.event] ?? CircleDot,
            event:
              activityLabels[entry.event] ?? entry.event.replaceAll("_", " "),
            title: incident.title,
            source: incident.source,
            id: incident.id,
          }))
        : [
            {
              at: incident.updated,
              icon: activityIcons[incident.status] ?? CircleDot,
              event: activityLabels[incident.status] ?? incident.status,
              title: incident.title,
              source: incident.source,
              id: incident.id,
            },
          ];
    const runs = incident.manualActionHistory.map((run) => ({
      at: String(run.at ?? incident.updated),
      icon: ShieldAlert,
      event: `manual action ${String(run.status ?? "run")}`,
      title: incident.title,
      source: incident.source,
      id: incident.id,
    }));
    return [...timeline, ...runs];
  });
  const lifecycleEvents = agentEvents.map((entry) => ({
    at: entry.at,
    icon:
      entry.status === AGENT_STATUS.ACTIVE
        ? CheckCircle2
        : entry.status === AGENT_STATUS.IDLE
          ? CircleDot
          : XCircle,
    event: `agent ${entry.status}`,
    title: `${entry.domain} is ${entry.status}`,
    source: "agent",
    id: domain,
  }));
  const events = sortByTimestamp([...incidentEvents, ...lifecycleEvents], true);
  return (
    <section
      className="activity-panel console-panel"
      aria-label="Agent activity feed"
    >
      {events.length === 0 ? (
        <div className="panel-placeholder">
          <Activity size={25} />
          <h2>No activity yet</h2>
          <p>{domain}’s actions will appear here as alerts are processed.</p>
        </div>
      ) : (
        <div className="activity-feed">
          {events.map((entry, index) => {
            const Icon = entry.icon;
            return (
              <article
                className="activity-item"
                key={`${entry.id}-${entry.at}-${index}`}
              >
                <span className="activity-icon">
                  <Icon size={14} />
                </span>
                <div className="activity-item-body">
                  <div>
                    <strong>{entry.event}</strong>
                    <time dateTime={entry.at}>{formatTimestamp(entry.at)}</time>
                  </div>
                  <p>{entry.title}</p>
                  <small>
                    {entry.source} · {entry.id}
                  </small>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
