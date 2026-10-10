import { controlRequest } from "../api";
import { INCIDENT_STATUS, toIncident, type Incident } from "../model";

export async function replayIncident(
  apiBase: string,
  incident: Incident,
): Promise<Incident | null> {
  const prompt =
    incident.status === INCIDENT_STATUS.BLOCKED
      ? (window.prompt(
          "Tell the agent what to reconsider before replaying this blocked incident",
        ) ?? "")
      : "";
  if (incident.status === INCIDENT_STATUS.BLOCKED && !prompt.trim())
    return null;
  const response = await controlRequest(
    `${apiBase}/incidents/replay/${incident.id}`,
    {
      method: "POST",
      body: JSON.stringify({
        prompt:
          incident.status === INCIDENT_STATUS.BLOCKED ? prompt : undefined,
      }),
    },
    "Replay rejected",
  );
  return !response || response.status === 202
    ? null
    : toIncident(await response.json());
}

export async function ignoreIncident(
  apiBase: string,
  incident: Incident,
): Promise<boolean> {
  return Boolean(
    await controlRequest(
      `${apiBase}/incidents/${incident.id}/ignore`,
      { method: "POST" },
      "Ignore rejected",
    ),
  );
}

export async function deleteIncident(
  apiBase: string,
  incident: Incident,
): Promise<boolean> {
  return Boolean(
    await controlRequest(
      `${apiBase}/incidents/${incident.id}`,
      { method: "DELETE" },
      "Delete rejected",
    ),
  );
}

export async function executeManualAction(
  apiBase: string,
  incident: Incident,
  index: number,
): Promise<Incident | null> {
  const response = await controlRequest(
    `${apiBase}/incidents/${incident.id}/manual-actions/execute`,
    {
      method: "POST",
      body: JSON.stringify({ action_index: index }),
    },
    "Manual action rejected",
  );
  return !response || response.status === 202
    ? null
    : toIncident(await response.json());
}
