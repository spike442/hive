import { controlRequest, getJson } from "../api";
import { AGENT_STATUS, type ManagedAgent, type UiConfig } from "../model";

export async function loadHiveConfig(): Promise<UiConfig> {
  return getJson<UiConfig>("/config", { cache: "no-store" });
}

export async function loadHiveVersion(apiBase: string): Promise<string> {
  const data = await getJson<{ version: string }>(`${apiBase}/version`, {
    cache: "no-store",
  });
  return data.version;
}

export async function loadAgents(
  apiBase: string,
  signal: AbortSignal,
): Promise<ManagedAgent[]> {
  const data = await getJson<{ agents: ManagedAgent[] }>(`${apiBase}/agents`, {
    cache: "no-store",
    signal,
  });
  return data.agents;
}

export async function setAgentStatus(
  apiBase: string,
  domain: string,
  status: typeof AGENT_STATUS.ACTIVE | typeof AGENT_STATUS.IDLE,
): Promise<boolean> {
  return Boolean(
    await controlRequest(
      `${apiBase}/agents/${domain}/${status}`,
      { method: "POST" },
      `${domain} status change failed`,
    ),
  );
}
