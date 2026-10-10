import type { ReactNode } from "react";
import {
  Archive,
  ChevronRight,
  FileCode2,
  Github,
  MessageSquare,
  Search,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { formatTimestamp, sortByTimestamp } from "../format";
import {
  DIAGNOSIS_STATUS,
  INCIDENT_EVENT,
  INCIDENT_STATUS,
  statusFilters,
  type Incident,
} from "../model";

import { StatusIcon } from "./StatusIcon";

type IncidentListProps = {
  incidents: Incident[];
  filtered: Incident[];
  selectedId: string;
  query: string;
  sourceFilter: string;
  statusFilter: string;
  sourceCounts: Record<string, number>;
  statusCounts: Record<string, number>;
  onQueryChange: (value: string) => void;
  onSourceFilterChange: (value: string) => void;
  onStatusFilterChange: (value: string) => void;
  onSelect: (id: string) => void;
  onRefresh: () => void;
  updatedAt?: string;
};

export function IncidentList({
  incidents,
  filtered,
  selectedId,
  query,
  sourceFilter,
  statusFilter,
  sourceCounts,
  statusCounts,
  onQueryChange,
  onSourceFilterChange,
  onStatusFilterChange,
  onSelect,
  onRefresh,
  updatedAt,
}: IncidentListProps) {
  const sources = [
    ...new Set(incidents.map((incident) => incident.source)),
  ].sort();
  const allCount = incidents.filter(
    (incident) => incident.status !== INCIDENT_STATUS.IGNORED,
  ).length;
  return (
    <section className="incident-list-panel console-panel">
      <label className="search-box">
        <Search size={15} />
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Search incidents"
        />
      </label>
      <button className="action-button filter-refresh" onClick={onRefresh}>
        <RefreshCw size={14} /> Refresh
      </button>
      <div className="incident-filters">
        <FilterGroup
          label="Source"
          value={sourceFilter}
          values={sources}
          counts={sourceCounts}
          allCount={allCount}
          onChange={onSourceFilterChange}
        />
        <FilterGroup
          label="Status"
          value={statusFilter}
          values={statusFilters}
          counts={statusCounts}
          allCount={allCount}
          onChange={onStatusFilterChange}
        />
      </div>
      <div className="incident-list">
        {filtered.map((incident) => (
          <button
            className={`incident-row ${incident.id === selectedId ? "selected" : ""}`}
            key={incident.id}
            onClick={() => onSelect(incident.id)}
          >
            <div className="incident-row-icon">
              <StatusIcon status={incident.status} />
            </div>
            <div className="incident-row-body">
              <strong>{incident.title}</strong>
              <span>
                {incident.source} · {formatTimestamp(incident.updated)}
              </span>
            </div>
            <ChevronRight size={15} className="row-chevron" />
          </button>
        ))}
      </div>
      {updatedAt && (
        <small className="incident-menu-updated">
          Updated {formatTimestamp(updatedAt)}
        </small>
      )}
    </section>
  );
}

function FilterGroup({
  label,
  value,
  values,
  counts,
  allCount,
  onChange,
}: {
  label: string;
  value: string;
  values: string[];
  counts: Record<string, number>;
  allCount: number;
  onChange: (next: string) => void;
}) {
  return (
    <div className="filter-group">
      <span>{label}</span>
      <button className={!value ? "active" : ""} onClick={() => onChange("")}>
        All <small className="filter-count">{allCount}</small>
      </button>
      {values.map((option) => (
        <button
          className={value === option ? "active" : ""}
          key={option}
          onClick={() => onChange(value === option ? "" : option)}
        >
          {option.replace("_", " ")}{" "}
          <small className="filter-count">{counts[option] ?? 0}</small>
        </button>
      ))}
    </div>
  );
}

export function IncidentThread({
  incident,
  domain,
}: {
  incident: Incident;
  domain: string;
}) {
  const replayEvents = incident.timeline
    .filter((entry) => entry.event === INCIDENT_EVENT.REPLAYED && entry.prompt)
    .map((entry) => ({
      at: entry.at,
      role: "operator" as const,
      text: entry.prompt!,
      status: undefined,
      actions: [] as string[],
    }));
  const knownPrompts = new Set(replayEvents.map((entry) => entry.text));
  const legacyPrompts = incident.replayPrompts
    .filter((prompt) => !knownPrompts.has(prompt))
    .map((prompt) => ({
      at: incident.replayedAt ?? incident.updated,
      role: "operator" as const,
      text: prompt,
      status: undefined,
      actions: [] as string[],
    }));
  const suggestions = incident.diagnosisHistory
    .filter(
      (entry) =>
        entry.diagnosis.status !== INCIDENT_STATUS.ACKNOWLEDGED &&
        entry.diagnosis.status !== DIAGNOSIS_STATUS.OBSERVED,
    )
    .map((entry) => ({
      at: entry.at,
      role: "agent" as const,
      status: entry.diagnosis.status,
      text:
        entry.diagnosis.hypothesis ||
        entry.diagnosis.incident ||
        "No suggestion recorded.",
      actions:
        entry.diagnosis.manual_actions?.map((action) => action.title) ?? [],
    }));
  const messages = sortByTimestamp([
    ...replayEvents,
    ...legacyPrompts,
    ...suggestions,
  ]);
  if (messages.length === 0) return null;
  return (
    <div
      className="detail-section incident-thread"
      aria-label="Incident conversation"
    >
      <div className="detail-section-title">
        <MessageSquare size={15} /> Incident thread
      </div>
      <div className="thread-messages">
        {messages.map((message, index) => (
          <article
            className={`thread-message ${message.role}`}
            key={`${message.at}-${index}`}
          >
            <div className="thread-message-meta">
              <strong>{message.role === "operator" ? "You" : domain}</strong>
              <time dateTime={message.at}>{formatTimestamp(message.at)}</time>
            </div>
            <p>{message.text}</p>
            {message.role === "agent" && (
              <>
                {message.status && (
                  <small className="thread-status">{message.status}</small>
                )}
                {message.actions.length > 0 && (
                  <small className="thread-actions">
                    Manual actions: {message.actions.join(" · ")}
                  </small>
                )}
              </>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}

type IncidentDetailProps = {
  domain: string;
  incident: Incident;
  actionsDisabled: boolean;
  retrying: boolean;
  onReplay: (incident: Incident) => void;
  onIgnore: (incident: Incident) => void;
  onDelete: (incident: Incident) => void;
  manualActions: ReactNode;
};

export function IncidentDetail({
  domain,
  incident,
  actionsDisabled,
  retrying,
  onReplay,
  onIgnore,
  onDelete,
  manualActions,
}: IncidentDetailProps) {
  return (
    <section className="detail-panel console-panel">
      <div className="detail-heading">
        <div>
          <h2>{incident.title}</h2>
          <p>{incident.summary}</p>
        </div>
      </div>
      <div className="metric-row">
        <Metric label="STATUS" value={incident.status} />
        <Metric
          label="CONFIDENCE"
          value={incident.confidence}
          className={incident.confidence}
        />
        <Metric
          label="RISK LEVEL"
          value={incident.risk}
          className={incident.risk}
        />
        <Metric label="SOURCE" value={incident.source} />
      </div>
      <div className="alert-gadget">
        <div className="field-grid">
          <Field label="ALERT" value={incident.alertname} />
          <Field label="STATE" value={incident.alertStatus} />
          <Field label="SOURCE" value={incident.source} />
          <Field label="SEVERITY" value={incident.severity} />
          <Field label="NAMESPACE" value={incident.namespace || "—"} />
          <Field label="POD" value={incident.pod || "—"} />
          <Field label="STARTED" value={formatTimestamp(incident.startsAt)} />
          <Field
            label="REPLAYED"
            value={formatTimestamp(incident.replayedAt)}
          />
        </div>
      </div>
      <IncidentThread incident={incident} domain={domain} />
      {incident.evidence.length > 0 && (
        <div className="detail-section">
          <div className="detail-section-title">
            <Search size={15} /> Investigation evidence
          </div>
          <ul>
            {incident.evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {incident.files.length > 0 && (
        <div className="detail-section">
          <div className="detail-section-title">
            <FileCode2 size={15} /> Proposed files
          </div>
          {incident.files.map((file) => (
            <a
              className="file-chip"
              href={
                incident.pullRequestUrl
                  ? `${incident.pullRequestUrl}/files`
                  : `https://github.com/spike442/homelab/blob/main/${file}`
              }
              target="_blank"
              rel="noreferrer"
              key={file}
            >
              <FileCode2 size={13} />
              {file}
            </a>
          ))}
        </div>
      )}
      <div className="action-bar">
        {incident.actions.includes("replay") && (
          <button
            className="action-button"
            onClick={() => onReplay(incident)}
            disabled={actionsDisabled || retrying}
          >
            <RefreshCw size={15} /> {retrying ? "Replaying" : "Replay"}
          </button>
        )}
        {incident.actions.includes("ignore") && (
          <button
            className="action-button"
            onClick={() => onIgnore(incident)}
            disabled={actionsDisabled}
          >
            <Archive size={15} /> Ignore
          </button>
        )}
        {incident.actions.includes("open-pr") && incident.pullRequestUrl && (
          <a
            className={`action-button primary ${actionsDisabled ? "disabled" : ""}`}
            href={actionsDisabled ? undefined : incident.pullRequestUrl}
            aria-disabled={actionsDisabled}
            onClick={(event) => {
              if (actionsDisabled) event.preventDefault();
            }}
            target="_blank"
            rel="noreferrer"
          >
            <Github size={15} /> Open PR
          </a>
        )}
        {incident.actions.includes("delete") && (
          <button
            className="action-button danger"
            onClick={() => onDelete(incident)}
            disabled={actionsDisabled}
          >
            <Trash2 size={15} /> Delete
          </button>
        )}
      </div>
      {manualActions}
    </section>
  );
}

function Metric({
  label,
  value,
  className = "",
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div>
      <span>{label}</span>
      <strong className={className ? `level ${className}` : ""}>{value}</strong>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
