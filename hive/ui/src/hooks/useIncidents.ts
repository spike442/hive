import { useState } from "react";
import { loadIncidents } from "../api";
import type { Incident } from "../model";
import { usePolling } from "./usePolling";

export function useIncidents(
  apiBase: string,
  refreshKey: number,
  enabled: boolean,
) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  usePolling(enabled ? apiBase : "", refreshKey, async (signal) => {
    try {
      const loaded = await loadIncidents(apiBase, signal);
      if (signal.aborted) return;
      setIncidents(loaded);
      setError("");
    } catch (reason) {
      if (!signal.aborted)
        setError(
          reason instanceof Error ? reason.message : "Incidents unavailable.",
        );
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  });
  return { incidents, setIncidents, loading, error };
}
