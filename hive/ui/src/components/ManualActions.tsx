import { useState } from "react";
import { ShieldAlert } from "lucide-react";
import { executeManualAction } from "../api/incidents";
import { formatTimestamp } from "../format";
import { INCIDENT_STATUS, type Incident } from "../model";

export function ManualActions({
  incident,
  apiBase,
  onUpdated,
  onError,
}: {
  incident: Incident;
  apiBase: string;
  onUpdated: (incident: Incident) => void;
  onError: (message: string) => void;
}) {
  const [running, setRunning] = useState<number | null>(null);
  const canApprove =
    incident.status === INCIDENT_STATUS.BLOCKED &&
    incident.manualActions.length > 0;
  const hasRuns = incident.manualActionHistory.length > 0;
  if (!canApprove && !hasRuns) return null;
  async function execute(index: number) {
    if (
      !window.confirm(
        `Approve and run this command?\n\n$ ${incident.manualActions[index].command}`,
      )
    )
      return;
    setRunning(index);
    try {
      const updated = await executeManualAction(apiBase, incident, index);
      if (updated) onUpdated(updated);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Manual action failed.");
    } finally {
      setRunning(null);
    }
  }
  return (
    <section className="manual-actions" aria-label="Manual actions and runs">
      {canApprove && (
        <>
          <div className="detail-section-title">
            <ShieldAlert size={15} /> Manual action approval
          </div>
          <small className="incident-updated">
            Incident updated: {formatTimestamp(incident.updated)}
          </small>
          {incident.manualActions.map((action, index) => (
            <div className="manual-action" key={`${action.command}-${index}`}>
              <strong>{action.title}</strong>
              <pre className="manual-command">
                <code>$ {action.command}</code>
              </pre>
              <p>{action.reason}</p>
              <small>Validation: {action.validation}</small>
              {incident.manualActionHistory
                .filter((run) => run.action_index === index)
                .slice(-1)
                .map((run) => (
                  <small
                    key={`${String(run.at)}-${index}`}
                    className="manual-action-result"
                  >
                    Last run: {String(run.status)}
                    {run.exit_code !== undefined
                      ? ` (exit ${String(run.exit_code)})`
                      : ""}
                    {run.error ? ` — ${String(run.error)}` : ""}
                  </small>
                ))}
              <button
                className="action-button"
                onClick={() => void execute(index)}
                disabled={running !== null}
              >
                {running === index ? "Running…" : "Approve & run"}
              </button>
            </div>
          ))}
        </>
      )}
      {hasRuns && (
        <div className="manual-runs" aria-label="Manual action runs">
          {incident.manualActionHistory
            .slice()
            .reverse()
            .map((run, index) => (
              <div className="manual-run" key={`${String(run.at)}-${index}`}>
                <div>
                  <strong>
                    {String(run.status)}
                    {run.exit_code !== undefined
                      ? ` · exit ${String(run.exit_code)}`
                      : ""}
                  </strong>
                  <small>{String(run.at ?? "")}</small>
                </div>
                <code>{String(run.command ?? "manual action")}</code>
                {typeof run.error === "string" && (
                  <small className="manual-run-error">{run.error}</small>
                )}
              </div>
            ))}
        </div>
      )}
    </section>
  );
}
