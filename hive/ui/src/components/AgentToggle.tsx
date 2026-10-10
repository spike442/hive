import { AGENT_STATUS, type AgentStatus } from "../model";

const labels: Record<AgentStatus, string> = {
  [AGENT_STATUS.ACTIVE]: "ON",
  [AGENT_STATUS.IDLE]: "IDLE",
  [AGENT_STATUS.DOWN]: "DOWN",
};

export function AgentToggle({
  domain,
  status,
  onToggle,
}: {
  domain: string;
  status: AgentStatus;
  onToggle: () => void;
}) {
  const unavailable = status === AGENT_STATUS.DOWN;
  const idle = status === AGENT_STATUS.IDLE;
  const action = unavailable ? "unavailable" : idle ? "start" : "set idle";
  return (
    <button
      className={`agent-switch ${status}`}
      onClick={onToggle}
      aria-label={`${domain}: ${action}`}
      aria-pressed={idle}
      disabled={unavailable}
    >
      <span className="agent-switch-label">{labels[status]}</span>
      <span className="agent-switch-knob" />
    </button>
  );
}
