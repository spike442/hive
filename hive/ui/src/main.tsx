import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  CircleDot,
  LayoutDashboard,
  RefreshCw,
  RadioTower,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import "./styles.css";
import {
  deleteIncident,
  ignoreIncident,
  replayIncident,
} from "./api/incidents";
import { loadHiveConfig, loadHiveVersion } from "./api/hive";
import { checkReviews, deleteReview, retryReview } from "./api/reviews";
import {
  AGENT_STATUS,
  CLOSED_INCIDENT_STATUSES,
  INCIDENT_STATUS,
  statusFilters,
  type Incident,
  type Panel,
  type PullRequestReview,
  type UiConfig,
} from "./model";
import { OverviewPanel, HiveDashboard } from "./components/Dashboards";
import { AgentToggle } from "./components/AgentToggle";
import { useAgents } from "./hooks/useAgents";
import { useIncidents } from "./hooks/useIncidents";
import { useReviews } from "./hooks/useReviews";

const IncidentDetail = lazy(() =>
  import("./components/IncidentViews").then((module) => ({
    default: module.IncidentDetail,
  })),
);
const IncidentList = lazy(() =>
  import("./components/IncidentViews").then((module) => ({
    default: module.IncidentList,
  })),
);
const ManualActions = lazy(() =>
  import("./components/ManualActions").then((module) => ({
    default: module.ManualActions,
  })),
);
const ActivityFeed = lazy(() =>
  import("./components/IncidentActivity").then((module) => ({
    default: module.ActivityFeed,
  })),
);
const PrReviewPanel = lazy(() =>
  import("./components/PrReviewPanel").then((module) => ({
    default: module.PrReviewPanel,
  })),
);

const panels: { label: Panel; icon: typeof LayoutDashboard }[] = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Incidents", icon: ShieldAlert },
  { label: "Activity", icon: Activity },
];

function App() {
  const [selectedId, setSelectedId] = useState("");
  const [activePanel, setActivePanel] = useState<Panel>("Overview");
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedAgent, setSelectedAgent] = useState("hive");
  const [checkingReviews, setCheckingReviews] = useState(false);
  const [retryingReviewId, setRetryingReviewId] = useState<number | null>(null);
  const [retryingId, setRetryingId] = useState("");
  const [statusNotification, setStatusNotification] = useState("");
  const [runtimeConfig, setRuntimeConfig] = useState<UiConfig | null>(null);
  const [configurationError, setConfigurationError] = useState("");
  const [version, setVersion] = useState("—");
  const [refreshToken, setRefreshToken] = useState(0);
  const notificationTimer = useRef<number | undefined>(undefined);
  const hiveApiBase = runtimeConfig?.hive_url ?? "";
  const notify = (message: string) => {
    window.clearTimeout(notificationTimer.current);
    setStatusNotification(message);
    notificationTimer.current = window.setTimeout(
      () => setStatusNotification(""),
      4500,
    );
  };
  useEffect(() => () => window.clearTimeout(notificationTimer.current), []);
  const agentResource = useAgents(hiveApiBase, refreshToken, notify);
  const { agents } = agentResource;
  const sreAgent = agents.find((agent) => agent.domain === "sre");
  const reviewAgent = agents.find((agent) => agent.domain === "pr-review");
  const selectedDomain = selectedAgent;
  const domain = sreAgent?.domain ?? "";
  const sreStatus = sreAgent?.status ?? AGENT_STATUS.DOWN;
  const reviewStatus = reviewAgent?.status ?? AGENT_STATUS.DOWN;
  const agentEvents = agentResource.events.filter(
    (event) => event.domain === domain,
  );
  const { incidents, setIncidents, loading, error } = useIncidents(
    hiveApiBase,
    refreshToken,
    Boolean(sreAgent),
  );
  const {
    reviews,
    setReviews,
    error: reviewsError,
  } = useReviews(hiveApiBase, refreshToken, Boolean(reviewAgent));
  useEffect(() => {
    void loadHiveConfig()
      .then(setRuntimeConfig)
      .catch((reason: unknown) => {
        setConfigurationError(
          reason instanceof Error
            ? reason.message
            : "Hive configuration unavailable.",
        );
      });
  }, []);
  useEffect(() => {
    if (!hiveApiBase) return;
    let active = true;
    void loadHiveVersion(hiveApiBase)
      .then((value) => {
        if (active) setVersion(value);
      })
      .catch(() => {
        if (active) setVersion("—");
      });
    return () => {
      active = false;
    };
  }, [hiveApiBase, refreshToken]);
  const visibleIncidents = useMemo(
    () =>
      incidents.filter(
        (incident) => incident.status !== INCIDENT_STATUS.IGNORED,
      ),
    [incidents],
  );
  const sourceCounts = useMemo(
    () =>
      Object.fromEntries(
        [...new Set(visibleIncidents.map((incident) => incident.source))].map(
          (source) => [
            source,
            visibleIncidents.filter((item) => item.source === source).length,
          ],
        ),
      ),
    [visibleIncidents],
  );
  const statusCounts = useMemo(
    () =>
      Object.fromEntries(
        statusFilters.map((status) => [
          status,
          incidents.filter((incident) => incident.status === status).length,
        ]),
      ),
    [incidents],
  );
  const filtered = useMemo(
    () =>
      incidents.filter(
        (incident) =>
          (statusFilter
            ? incident.status === statusFilter
            : incident.status !== INCIDENT_STATUS.IGNORED) &&
          (!sourceFilter || incident.source === sourceFilter) &&
          `${incident.title} ${incident.summary} ${incident.source}`
            .toLowerCase()
            .includes(query.toLowerCase()),
      ),
    [incidents, query, sourceFilter, statusFilter],
  );
  const selected =
    filtered.find((incident) => incident.id === selectedId) ?? filtered[0];
  const openCount = incidents.filter(
    (incident) => !CLOSED_INCIDENT_STATUSES.has(incident.status),
  ).length;
  async function checkPullRequests() {
    if (reviewStatus === AGENT_STATUS.DOWN) return;
    setCheckingReviews(true);
    try {
      if (!(await checkReviews(hiveApiBase))) return;
      notify("Hive started checking pull requests.");
      setRefreshToken((value) => value + 1);
    } catch (reason) {
      notify(
        reason instanceof Error ? reason.message : "Pull-request check failed.",
      );
    } finally {
      setCheckingReviews(false);
    }
  }
  async function retryPullRequestReview(review: PullRequestReview) {
    setRetryingReviewId(review.id);
    try {
      if (await retryReview(hiveApiBase, review)) {
        setRefreshToken((current) => current + 1);
        notify("Review retry sent.");
      }
    } finally {
      setRetryingReviewId(null);
    }
  }

  async function deletePullRequestReview(review: PullRequestReview) {
    if (
      !window.confirm(
        `Delete review for ${review.repository} #${review.pull_request_number}?`,
      )
    )
      return;
    if (!(await deleteReview(hiveApiBase, review))) return;
    setReviews((current) => current.filter((item) => item.id !== review.id));
  }
  async function replaySelectedIncident(incident: Incident) {
    setRetryingId(incident.id);
    try {
      const updated = await replayIncident(hiveApiBase, incident);
      if (updated) updateIncident(updated);
    } finally {
      setRetryingId("");
    }
  }
  async function ignoreSelectedIncident(incident: Incident) {
    if (!(await ignoreIncident(hiveApiBase, incident))) return;
    updateIncident({ ...incident, status: INCIDENT_STATUS.IGNORED });
  }
  async function deleteSelectedIncident(incident: Incident) {
    if (
      !window.confirm(
        `Delete incident “${incident.title}”? This cannot be undone.`,
      )
    )
      return;
    if (!(await deleteIncident(hiveApiBase, incident))) return;
    setIncidents((current) =>
      current.filter((item) => item.id !== incident.id),
    );
    setSelectedId((current) => (current === incident.id ? "" : current));
  }
  function updateIncident(updated: Incident) {
    setIncidents((current) =>
      current.map((item) => (item.id === updated.id ? updated : item)),
    );
  }
  async function runAction(action: () => Promise<void>) {
    try {
      await action();
    } catch (error) {
      notify(error instanceof Error ? error.message : "Action failed.");
    }
  }
  return (
    <div className="app-shell">
      <aside className="agent-tower">
        <div className="tower-header">
          <button
            className="brand-mark"
            aria-label="Open Hive dashboard"
            onClick={() => setSelectedAgent("hive")}
          >
            <RadioTower size={19} />
          </button>
        </div>
        {agents.map((agent) => (
          <button
            key={agent.domain}
            className={`agent-card ${selectedAgent === agent.domain ? "selected" : ""} ${agent.status}`}
            onClick={() => setSelectedAgent(agent.domain)}
            aria-label={`${agent.domain} is ${agent.status}`}
          >
            <img
              className="agent-avatar"
              src={`/${agent.domain}.png`}
              alt={agent.domain}
            />
            <span className="agent-name">{agent.domain}</span>
            <span className={`agent-state-dot ${agent.status}`} />
          </button>
        ))}
        <div className="tower-footer" />
      </aside>
      <main className="main-content">
        {(configurationError || agentResource.error) && (
          <p role="alert">{configurationError || agentResource.error}</p>
        )}
        {statusNotification && (
          <div className="status-toast" role="status">
            <CircleDot size={14} /> {statusNotification}
          </div>
        )}
        {selectedDomain === "sre" && sreAgent && (
          <>
            <header className="console-header compact">
              <div className="header-readout">
                <AgentToggle
                  domain={domain}
                  status={sreStatus}
                  onToggle={() =>
                    void runAction(() => agentResource.toggle(sreAgent))
                  }
                />
              </div>
            </header>
            <nav className="panel-tabs" aria-label="Agent panels">
              {panels.map(({ label, icon: Icon }) => (
                <button
                  className={activePanel === label ? "active" : ""}
                  key={label}
                  onClick={() => setActivePanel(label)}
                >
                  <Icon size={15} /> {label}
                  {label === "Incidents" && <b>{openCount}</b>}
                </button>
              ))}
            </nav>
          </>
        )}
        <Suspense
          fallback={
            <div className="panel-placeholder" role="status">
              Loading panel…
            </div>
          }
        >
          {selectedAgent === "hive" ? (
            <HiveDashboard
              version={version}
              agents={agents}
              incidents={incidents}
              agentEvents={agentResource.events}
              reviews={reviews}
              onSelectAgent={setSelectedAgent}
            />
          ) : selectedDomain === "pr-review" && reviewAgent ? (
            <PrReviewPanel
              status={reviewStatus}
              domain={reviewAgent.domain}
              version={reviewAgent.version}
              error={reviewsError}
              reviews={reviews}
              checking={checkingReviews}
              retryingId={retryingReviewId}
              onRetry={(review) =>
                void runAction(() => retryPullRequestReview(review))
              }
              onDelete={(review) =>
                void runAction(() => deletePullRequestReview(review))
              }
              onToggle={() =>
                void runAction(() => agentResource.toggle(reviewAgent))
              }
              onCheck={() => void checkPullRequests()}
            />
          ) : activePanel === "Incidents" ? (
            loading ? (
              <div className="panel-placeholder console-panel">
                <RefreshCw size={25} className="spin" />
                <h2>Loading incidents</h2>
                <p>Loading incidents.</p>
              </div>
            ) : error ? (
              <div className="panel-placeholder console-panel">
                <XCircle size={25} />
                <h2>API unavailable</h2>
                <p>{error}</p>
              </div>
            ) : (
              <div className="content-grid">
                <IncidentList
                  updatedAt={selected?.updated}
                  incidents={incidents}
                  filtered={filtered}
                  selectedId={selected?.id ?? ""}
                  query={query}
                  sourceFilter={sourceFilter}
                  statusFilter={statusFilter}
                  sourceCounts={sourceCounts}
                  statusCounts={statusCounts}
                  onQueryChange={setQuery}
                  onSourceFilterChange={setSourceFilter}
                  onStatusFilterChange={setStatusFilter}
                  onSelect={setSelectedId}
                  onRefresh={() => setRefreshToken((value) => value + 1)}
                />
                {selected ? (
                  <IncidentDetail
                    domain={domain}
                    manualActions={
                      <ManualActions
                        key={selected.id}
                        incident={selected}
                        apiBase={hiveApiBase}
                        onUpdated={updateIncident}
                        onError={notify}
                      />
                    }
                    incident={selected}
                    actionsDisabled={
                      selected.status === INCIDENT_STATUS.PROCESSING
                    }
                    retrying={retryingId === selected.id}
                    onReplay={(item) =>
                      void runAction(() => replaySelectedIncident(item))
                    }
                    onIgnore={(item) =>
                      void runAction(() => ignoreSelectedIncident(item))
                    }
                    onDelete={(item) =>
                      void runAction(() => deleteSelectedIncident(item))
                    }
                  />
                ) : (
                  <section className="detail-panel console-panel">
                    <div className="panel-placeholder">
                      <ShieldAlert size={25} />
                      <h2>No matching incidents</h2>
                      <p>Adjust the search or filters to see an incident.</p>
                    </div>
                  </section>
                )}
              </div>
            )
          ) : activePanel === "Activity" ? (
            <ActivityFeed
              incidents={incidents}
              agentEvents={agentEvents}
              domain={domain}
            />
          ) : (
            <OverviewPanel
              incidents={incidents}
              agentStatus={sreStatus}
              agentEvents={agentEvents}
              domain={domain}
            />
          )}
        </Suspense>
        <footer className="main-footer">
          <small className="app-version">v{version}</small>
        </footer>
      </main>
    </div>
  );
}

export default App;
createRoot(document.getElementById("root")!).render(<App />);
