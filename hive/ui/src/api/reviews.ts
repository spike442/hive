import { controlRequest } from "../api";
import type { PullRequestReview } from "../model";

export async function checkReviews(apiBase: string): Promise<boolean> {
  return Boolean(
    await controlRequest(
      `${apiBase}/events/reviews/check`,
      { method: "POST" },
      "Hive review check failed",
    ),
  );
}

export async function deleteReview(
  apiBase: string,
  review: PullRequestReview,
): Promise<boolean> {
  return Boolean(
    await controlRequest(
      `${apiBase}/reviews/${review.id}`,
      { method: "DELETE" },
      "Review deletion failed",
    ),
  );
}

export async function retryReview(
  apiBase: string,
  review: PullRequestReview,
): Promise<boolean> {
  return Boolean(
    await controlRequest(
      `${apiBase}/reviews/${review.id}/retry`,
      { method: "POST" },
      "Review retry failed",
    ),
  );
}
