import { useRef, useState } from "react";
import { loadAgents, setAgentStatus } from "../api/hive";
import { AGENT_STATUS, type AgentActivity, type ManagedAgent } from "../model";
import { usePolling } from "./usePolling";

export function useAgents(
  apiBase: string,
  refreshKey: number,
  notify: (message: string) => void,
) {
  const [agents, setAgents] = useState<ManagedAgent[]>([]);
  const [events, setEvents] = useState<AgentActivity[]>([]);
  const [error, setError] = useState("");
  const previous = useRef(new Map<string, ManagedAgent["status"]>());
  const failures = useRef(0);
  function record(loaded: ManagedAgent[]) {
    const changes = loaded.filter(
      (agent) => previous.current.get(agent.domain) !== agent.status,
    );
    for (const agent of changes) {
      if (previous.current.has(agent.domain))
        notify(`${agent.domain} is now ${agent.status}.`);
      previous.current.set(agent.domain, agent.status);
    }
    setAgents(loaded);
    if (changes.length)
      setEvents((current) =>
        [
          ...changes.map((agent) => ({
            domain: agent.domain,
            status: agent.status,
            at: new Date().toISOString(),
          })),
          ...current,
        ].slice(0, 100),
      );
  }
  usePolling(apiBase, refreshKey, async (signal) => {
    try {
      const loaded = await loadAgents(apiBase, signal);
      if (signal.aborted) return;
      failures.current = 0;
      setError("");
      record(loaded);
    } catch (reason) {
      if (signal.aborted) return;
      setError(
        reason instanceof Error ? reason.message : "Agent status unavailable.",
      );
      if (++failures.current >= 3)
        record(
          agents.map((agent) => ({
            ...agent,
            status: AGENT_STATUS.DOWN,
            healthy: false,
          })),
        );
    }
  });
  async function toggle(agent: ManagedAgent) {
    const status =
      agent.status === AGENT_STATUS.IDLE
        ? AGENT_STATUS.ACTIVE
        : AGENT_STATUS.IDLE;
    if (!(await setAgentStatus(apiBase, agent.domain, status))) return;
    record(
      agents.map((current) =>
        current.domain === agent.domain ? { ...current, status } : current,
      ),
    );
  }
  return { agents, events, error, toggle };
}
