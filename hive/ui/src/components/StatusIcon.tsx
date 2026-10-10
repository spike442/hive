import {
  Archive,
  CheckCircle2,
  CircleDot,
  GitPullRequest,
  XCircle,
} from "lucide-react";
import { INCIDENT_STATUS, type IncidentStatus } from "../model";

export function StatusIcon({ status }: { status: IncidentStatus }) {
  if (status === INCIDENT_STATUS.RESOLVED) return <CheckCircle2 size={15} />;
  if (status === INCIDENT_STATUS.BLOCKED || status === INCIDENT_STATUS.FAILED)
    return <XCircle size={15} />;
  if (status === INCIDENT_STATUS.PR_CREATED)
    return <GitPullRequest size={15} />;
  if (status === INCIDENT_STATUS.IGNORED) return <Archive size={15} />;
  return <CircleDot size={15} />;
}
