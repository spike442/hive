import { useState } from "react";
import { loadReviews } from "../api";
import type { PullRequestReview } from "../model";
import { usePolling } from "./usePolling";

export function useReviews(
  apiBase: string,
  refreshKey: number,
  enabled: boolean,
) {
  const [reviews, setReviews] = useState<PullRequestReview[]>([]);
  const [error, setError] = useState("");
  usePolling(enabled ? apiBase : "", refreshKey, async (signal) => {
    try {
      const loaded = await loadReviews(apiBase, signal);
      if (signal.aborted) return;
      setReviews(loaded);
      setError("");
    } catch (reason) {
      if (!signal.aborted)
        setError(
          reason instanceof Error ? reason.message : "Reviews unavailable.",
        );
    }
  });
  return { reviews, setReviews, error };
}
