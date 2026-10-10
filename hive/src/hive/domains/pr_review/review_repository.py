import json
from datetime import UTC, datetime

from core.domain import ReviewStatus
from sqlalchemy import text

from hive.persistence.database import Database


class ReviewRepository:
    """Persist pull-request reviews and merge outcomes."""

    def __init__(self, database: Database):
        self.database = database

    def acknowledge(self, pull_request: dict) -> None:
        with self.database.sessions.begin() as session:
            session.execute(
                text(
                    """
                    INSERT INTO reviews (owner, repository, pull_request_number, base_sha, head_sha,
                                         pull_request_url, status, updated_at)
                    VALUES (:owner, :repository, :number, :base_sha, :head_sha, :url, :status, :updated_at)
                    ON CONFLICT (owner, repository, pull_request_number, head_sha)
                    DO NOTHING
                    """
                ),
                {
                    "owner": pull_request["owner"],
                    "repository": pull_request["repository"],
                    "number": pull_request["number"],
                    "base_sha": pull_request["base_sha"],
                    "head_sha": pull_request["head_sha"],
                    "url": pull_request.get("html_url", ""),
                    "status": ReviewStatus.ACKNOWLEDGED.value,
                    "updated_at": datetime.now(UTC),
                },
            )

    def claim(self, pull_request: dict, workflow_id: str) -> bool:
        with self.database.sessions.begin() as session:
            claimed = session.execute(
                text(
                    """
                    INSERT INTO reviews (workflow_id, owner, repository, pull_request_number, base_sha, head_sha,
                                         pull_request_url, status, updated_at)
                    VALUES (:workflow_id, :owner, :repository, :number, :base_sha, :head_sha, :url, :status, NOW())
                    ON CONFLICT (owner, repository, pull_request_number, head_sha)
                    DO UPDATE SET workflow_id = EXCLUDED.workflow_id, status = EXCLUDED.status,
                                  updated_at = EXCLUDED.updated_at
                    WHERE reviews.workflow_id = :workflow_id
                       OR reviews.status IN (:acknowledged, :pending, :failed)
                    RETURNING id
                    """
                ),
                {
                    "workflow_id": workflow_id,
                    "owner": pull_request["owner"],
                    "repository": pull_request["repository"],
                    "number": pull_request["number"],
                    "base_sha": pull_request["base_sha"],
                    "head_sha": pull_request["head_sha"],
                    "url": pull_request.get("html_url", ""),
                    "status": ReviewStatus.PROCESSING.value,
                    "acknowledged": ReviewStatus.ACKNOWLEDGED.value,
                    "pending": ReviewStatus.PENDING.value,
                    "failed": ReviewStatus.FAILED.value,
                },
            )
            return claimed.scalar_one_or_none() is not None

    def fail(self, request: dict) -> None:
        pull_request = request["pull_request"]
        with self.database.sessions.begin() as session:
            session.execute(
                text(
                    "UPDATE reviews SET status = :status, summary = :reason, decision_reason = :reason, "
                    "review_actions = CAST(:actions AS jsonb), updated_at = NOW() "
                    "WHERE owner = :owner AND repository = :repository AND pull_request_number = :number "
                    "AND head_sha = :head_sha AND workflow_id = :workflow_id"
                ),
                {
                    "status": ReviewStatus.FAILED.value,
                    "reason": f"PR review workflow failed: {request['error']}.",
                    "actions": json.dumps(request.get("review_actions", [])),
                    "owner": pull_request["owner"],
                    "repository": pull_request["repository"],
                    "number": pull_request["number"],
                    "head_sha": pull_request["head_sha"],
                    "workflow_id": request["workflow_id"],
                },
            )

    def get(self, review_id: int) -> dict:
        with self.database.sessions() as session:
            row = (
                session.execute(text("SELECT * FROM reviews WHERE id = :id"), {"id": review_id})
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise LookupError(f"review not found: {review_id}")
            return dict(row)

    def is_merged(self, pull_request: dict) -> bool:
        with self.database.sessions() as session:
            return bool(
                session.execute(
                    text(
                        "SELECT 1 FROM reviews WHERE owner = :owner AND repository = :repository "
                        "AND pull_request_number = :number AND head_sha = :head_sha AND status = :status"
                    ),
                    {
                        "owner": pull_request["owner"],
                        "repository": pull_request["repository"],
                        "number": pull_request["number"],
                        "head_sha": pull_request["head_sha"],
                        "status": ReviewStatus.MERGED.value,
                    },
                ).scalar_one_or_none()
            )

    def save(self, result: dict, workflow_id: str) -> None:
        review = result.get("review") or result
        pull_request = result.get("pull_request") or review.get("pull_request") or {}
        if not pull_request:
            return
        status = review.get("status", ReviewStatus.FAILED.value)
        if status == ReviewStatus.PENDING.value:
            self.update_status(pull_request, status, review.get("reason", ""), workflow_id=workflow_id)
            return
        model_review = review.get("review", {})
        decision = review.get("decision", {})
        now = datetime.now(UTC)
        with self.database.sessions.begin() as session:
            updated = session.execute(
                text(
                    """
                    UPDATE reviews SET workflow_id = :workflow_id, status = :status, checks = CAST(:checks AS jsonb), risk = :risk,
                        confidence = :confidence, summary = :summary, findings = CAST(:findings AS jsonb),
                        mergeable = :mergeable, merge = :merge, decision_reason = :reason, reviewed_at = :reviewed_at,
                        updated_at = :updated_at, merged_at = :merged_at, merge_commit_sha = :sha,
                        review_actions = CAST(:actions AS jsonb)
                    WHERE owner = :owner AND repository = :repository AND pull_request_number = :number
                      AND head_sha = :head_sha AND workflow_id = :workflow_id
                    """
                ),
                {
                    "workflow_id": workflow_id,
                    "status": status,
                    "checks": json.dumps(review.get("checks", [])),
                    "risk": model_review.get("risk"),
                    "confidence": model_review.get("confidence"),
                    "summary": model_review.get("summary", ""),
                    "findings": json.dumps(model_review.get("findings", [])),
                    "mergeable": review.get("mergeable"),
                    "merge": decision.get("merge"),
                    "reason": decision.get("reason", ""),
                    "reviewed_at": now,
                    "updated_at": now,
                    "merged_at": review.get("merged_at"),
                    "sha": review.get("merge_commit_sha", ""),
                    "actions": json.dumps(review.get("review_actions", [])),
                    "owner": pull_request["owner"],
                    "repository": pull_request["repository"],
                    "number": pull_request["number"],
                    "head_sha": pull_request["head_sha"],
                },
            )
            if updated.rowcount != 1:
                raise LookupError(
                    f"review not found: {pull_request['owner']}/{pull_request['repository']}"
                    f"#{pull_request['number']}@{pull_request['head_sha']}"
                )

    def update_status(
        self,
        pull_request: dict,
        status: str,
        reason: str,
        review_actions: list[dict] | None = None,
        workflow_id: str | None = None,
    ) -> None:
        workflow_clause = " AND workflow_id = :workflow_id" if workflow_id else ""
        with self.database.sessions.begin() as session:
            updated = session.execute(
                text(
                    "UPDATE reviews SET status = :status, workflow_id = COALESCE(:workflow_id, workflow_id), "
                    "summary = :reason, decision_reason = :reason, "
                    "review_actions = COALESCE(CAST(:actions AS jsonb), review_actions), "
                    "updated_at = :updated_at WHERE owner = :owner AND repository = :repository "
                    "AND pull_request_number = :number AND head_sha = :head_sha" + workflow_clause
                ),
                {
                    "status": status,
                    "reason": reason,
                    "actions": json.dumps(review_actions) if review_actions is not None else None,
                    "workflow_id": workflow_id,
                    "updated_at": datetime.now(UTC),
                    "owner": pull_request["owner"],
                    "repository": pull_request["repository"],
                    "number": pull_request["number"],
                    "head_sha": pull_request["head_sha"],
                },
            )
            if updated.rowcount != 1:
                raise LookupError(
                    f"review not found: {pull_request['owner']}/{pull_request['repository']}"
                    f"#{pull_request['number']}@{pull_request['head_sha']}"
                )

    def mark_merged(
        self,
        pull_request: dict,
        workflow_id: str,
        merge_commit_sha: str,
        merged_at: datetime,
    ) -> None:
        with self.database.sessions.begin() as session:
            updated = session.execute(
                text(
                    "UPDATE reviews SET status = :status, merge = TRUE, merged_at = :merged_at, "
                    "merge_commit_sha = :sha, updated_at = :updated_at "
                    "WHERE owner = :owner AND repository = :repository AND pull_request_number = :number "
                    "AND head_sha = :head_sha AND workflow_id = :workflow_id"
                ),
                {
                    "merged_at": merged_at,
                    "status": ReviewStatus.MERGED.value,
                    "sha": merge_commit_sha,
                    "updated_at": datetime.now(UTC),
                    "owner": pull_request["owner"],
                    "repository": pull_request["repository"],
                    "number": pull_request["number"],
                    "head_sha": pull_request["head_sha"],
                    "workflow_id": workflow_id,
                },
            )
            if updated.rowcount != 1:
                raise LookupError(
                    f"review not found: {pull_request['owner']}/{pull_request['repository']}"
                    f"#{pull_request['number']}@{pull_request['head_sha']}"
                )

    def list(self, limit: int = 100, status: str | None = None) -> list[dict]:
        params: dict[str, object] = {"limit": limit}
        filter_sql = ""
        if status:
            filter_sql = "WHERE status = :status"
            params["status"] = status
        statement = text(
            f"""
            SELECT id, workflow_id, owner, repository, pull_request_number, base_sha, head_sha,
                   pull_request_url, status, checks, risk, confidence, summary, findings,
                   mergeable, merge, decision_reason, reviewed_at, updated_at, merged_at,
                   merge_commit_sha, review_actions
            FROM reviews {filter_sql}
            ORDER BY updated_at DESC, id DESC
            LIMIT :limit
            """
        )
        with self.database.sessions() as session:
            return [dict(row) for row in session.execute(statement, params).mappings()]

    def needs_review(self, pull_request: dict) -> bool:
        with self.database.sessions() as session:
            status = session.execute(
                text(
                    "SELECT status FROM reviews WHERE owner = :owner AND repository = :repository "
                    "AND pull_request_number = :number AND head_sha = :head_sha"
                ),
                {
                    "owner": pull_request["owner"],
                    "repository": pull_request["repository"],
                    "number": pull_request["number"],
                    "head_sha": pull_request["head_sha"],
                },
            ).scalar_one_or_none()
        return status is None or status in {
            ReviewStatus.ACKNOWLEDGED.value,
            ReviewStatus.PENDING.value,
            ReviewStatus.FAILED.value,
        }

    def delete(self, review_id: int) -> None:
        with self.database.sessions.begin() as session:
            deleted = session.execute(text("DELETE FROM reviews WHERE id = :id"), {"id": review_id})
            if deleted.rowcount != 1:
                raise LookupError(f"review not found: {review_id}")
