import { useState } from "react";
import {
  CircleDot,
  GitPullRequest,
  RefreshCw,
  Search,
  Trash2,
} from "lucide-react";
import { formatTimestamp } from "../format";
import { AgentToggle } from "./AgentToggle";
import {
  AGENT_STATUS,
  REVIEW_STATUS,
  type AgentStatus,
  type PullRequestReview,
} from "../model";

const reviewStatuses = Object.values(REVIEW_STATUS);

export function PrReviewPanel({
  domain,
  error,
  status,
  version,
  reviews,
  checking,
  retryingId,
  onRetry,
  onDelete,
  onToggle,
  onCheck,
}: {
  domain: string;
  error: string;
  status: AgentStatus;
  version: string;
  reviews: PullRequestReview[];
  checking: boolean;
  retryingId: number | null;
  onRetry: (review: PullRequestReview) => void;
  onDelete: (review: PullRequestReview) => void;
  onToggle: () => void;
  onCheck: () => void;
}) {
  const unavailable = status === AGENT_STATUS.DOWN;
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const filteredReviews = reviews.filter(
    (review) =>
      (!statusFilter || review.status === statusFilter) &&
      `${review.repository} ${review.pull_request_number} ${review.summary}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  const statusCount = (value: string) =>
    reviews.filter((review) => review.status === value).length;
  return (
    <section
      className="agent-panel console-panel"
      aria-label={`${domain} agent`}
    >
      <div className="agent-panel-heading">
        <img src={`/${domain}.png`} alt={domain} />
        <div>
          <span className="eyebrow">PR REVIEW AGENT</span>
          <h2>{domain}</h2>
          <p>
            Reviews configured pull requests and returns a risk and confidence
            decision.
          </p>
        </div>
      </div>
      <div className="agent-panel-metrics">
        <div>
          <span>STATUS</span>
          <strong className={status === AGENT_STATUS.ACTIVE ? "ready" : status}>
            {unavailable ? "unavailable" : status}
          </strong>
        </div>
        <div>
          <span>VERSION</span>
          <strong>{version}</strong>
        </div>
        <div>
          <span>ACCESS</span>
          <strong>read-only</strong>
        </div>
      </div>
      <AgentToggle domain={domain} status={status} onToggle={onToggle} />
      <button
        className="action-button primary"
        onClick={onCheck}
        disabled={unavailable || checking}
      >
        <RefreshCw size={14} className={checking ? "spin" : ""} />{" "}
        {checking ? "Checking…" : "Check now"}
      </button>
      <div className="agent-panel-note">
        <CircleDot size={15} /> {domain} polls configured repositories and
        validates each new pull-request revision.
      </div>
      <div className="review-dashboard">
        <div className="review-dashboard-heading">
          <div>
            <span className="eyebrow">CURRENT PULL REQUESTS</span>
            <strong>
              {filteredReviews.length} shown · {reviews.length} total
            </strong>
          </div>
        </div>
        <label className="search-box">
          <Search size={15} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search repository or summary"
          />
        </label>
        <div className="review-filters">
          <button
            className={!statusFilter ? "active" : ""}
            onClick={() => setStatusFilter("")}
          >
            All <small>{reviews.length}</small>
          </button>
          {reviewStatuses.map((value) => (
            <button
              className={statusFilter === value ? "active" : ""}
              key={value}
              onClick={() =>
                setStatusFilter(statusFilter === value ? "" : value)
              }
            >
              {value} <small>{statusCount(value)}</small>
            </button>
          ))}
        </div>
      </div>
      <div className="review-list">
        {error && <p role="alert">{error}</p>}
        {filteredReviews.length === 0 ? (
          <div className="panel-placeholder">
            <GitPullRequest size={22} />
            <p>
              {reviews.length === 0
                ? "No pull-request reviews yet."
                : "No reviews match the current filters."}
            </p>
          </div>
        ) : (
          filteredReviews.map((review) => (
            <article className="review-card" key={review.id}>
              <div>
                <a
                  href={review.pull_request_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <strong>
                    {review.repository} #{review.pull_request_number}
                  </strong>
                </a>
                <span className={`review-status ${review.status}`}>
                  {review.status}
                </span>
              </div>
              <p>{review.summary || "Review in progress…"}</p>
              <small>
                {formatTimestamp(review.updated_at)}
                {review.merge_commit_sha
                  ? ` · ${review.merge_commit_sha.slice(0, 8)}`
                  : ""}
              </small>
              <div className="review-meta">
                <span>
                  RISK <strong>{review.risk || "—"}</strong>
                </span>
                <span>
                  CONFIDENCE <strong>{review.confidence || "—"}</strong>
                </span>
              </div>
              {(review.status === REVIEW_STATUS.ACKNOWLEDGED ||
                review.status === REVIEW_STATUS.FAILED) && (
                <button
                  className="action-button"
                  onClick={() => onRetry(review)}
                  disabled={unavailable || retryingId === review.id}
                >
                  <RefreshCw size={14} />{" "}
                  {retryingId === review.id ? "Retrying…" : "Retry"}
                </button>
              )}
              <button
                className="action-button danger"
                onClick={() => onDelete(review)}
                disabled={
                  review.status === REVIEW_STATUS.PROCESSING ||
                  retryingId === review.id
                }
              >
                <Trash2 size={14} /> Delete
              </button>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
