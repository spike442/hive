import json
from datetime import UTC, datetime

from core.domain import ActionStatus, DiagnosisStatus, IncidentEvent, IncidentStatus
from sqlalchemy import text

from hive.persistence.database import Database


class IncidentRepository:
    """Persist SRE incidents and their treatment history."""

    def __init__(self, database: Database):
        self.database = database

    def queue(self, incident_id: str, alert: dict, workflow_id: str) -> str | None:
        now = datetime.now(UTC)
        with self.database.sessions.begin() as session:
            current = (
                session.execute(
                    text("SELECT status, workflow_id FROM incidents WHERE incident_id = :id FOR UPDATE"),
                    {"id": incident_id},
                )
                .mappings()
                .one_or_none()
            )
            if current is None:
                diagnosis = {"status": DiagnosisStatus.OBSERVED.value, "evidence": [], "validation": []}
                session.execute(
                    text(
                        "INSERT INTO incidents (incident_id, workflow_id, status, alert, diagnosis, updated_at, timeline) "
                        "VALUES (:id, :workflow_id, :status, CAST(:alert AS jsonb), CAST(:diagnosis AS jsonb), "
                        ":updated_at, CAST(:timeline AS jsonb))"
                    ),
                    {
                        "id": incident_id,
                        "workflow_id": workflow_id,
                        "status": IncidentStatus.ACKNOWLEDGED.value,
                        "alert": json.dumps(alert),
                        "diagnosis": json.dumps(diagnosis),
                        "updated_at": now,
                        "timeline": json.dumps([{"at": now.isoformat(), "event": IncidentEvent.ACKNOWLEDGED.value}]),
                    },
                )
                return workflow_id

            if current["status"] == IncidentStatus.IGNORED.value:
                return None

            if current["status"] == IncidentStatus.RESOLVED.value:
                session.execute(
                    text(
                        "UPDATE incidents SET workflow_id = :workflow_id, status = :status, alert = CAST(:alert AS jsonb), "
                        "updated_at = :updated_at, timeline = timeline || CAST(:event AS jsonb) WHERE incident_id = :id"
                    ),
                    {
                        "id": incident_id,
                        "workflow_id": workflow_id,
                        "status": IncidentStatus.ACKNOWLEDGED.value,
                        "alert": json.dumps(alert),
                        "updated_at": now,
                        "event": json.dumps([{"at": now.isoformat(), "event": IncidentEvent.REOPENED.value}]),
                    },
                )
                return workflow_id

            if current["status"] in {
                IncidentStatus.FAILED.value,
                IncidentStatus.BLOCKED.value,
                IncidentStatus.PENDING.value,
                IncidentStatus.PR_CREATED.value,
            }:
                return None

            if current["workflow_id"]:
                return current["workflow_id"]

            session.execute(
                text(
                    "UPDATE incidents SET workflow_id = :workflow_id, updated_at = :updated_at WHERE incident_id = :id"
                ),
                {"id": incident_id, "workflow_id": workflow_id, "updated_at": now},
            )
            return workflow_id

    def queue_replay(self, incident_id: str, workflow_id: str) -> bool:
        now = datetime.now(UTC)
        with self.database.sessions.begin() as session:
            updated = session.execute(
                text(
                    "UPDATE incidents SET workflow_id = :workflow_id, updated_at = :updated_at, "
                    "timeline = CASE WHEN workflow_id = :workflow_id THEN timeline "
                    "ELSE timeline || CAST(:event AS jsonb) END "
                    "WHERE incident_id = :id AND status IN (:acknowledged, :failed, :blocked)"
                ),
                {
                    "id": incident_id,
                    "workflow_id": workflow_id,
                    "updated_at": now,
                    "event": json.dumps([{"at": now.isoformat(), "event": IncidentEvent.REPLAYED.value}]),
                    "acknowledged": IncidentStatus.ACKNOWLEDGED.value,
                    "failed": IncidentStatus.FAILED.value,
                    "blocked": IncidentStatus.BLOCKED.value,
                },
            )
        return updated.rowcount == 1

    def mark_processing(
        self,
        incident_id: str,
        workflow_id: str,
        replay_prompt: str = "",
    ) -> bool:
        now = datetime.now(UTC)
        with self.database.sessions.begin() as session:
            updated = session.execute(
                text(
                    "UPDATE incidents SET workflow_id = :workflow_id, status = :status, updated_at = :updated_at, "
                    "replayed_at = CASE WHEN :prompt = '' OR status = :processing THEN replayed_at ELSE :updated_at END, "
                    "replay_prompts = CASE WHEN :prompt = '' OR status = :processing THEN replay_prompts "
                    "ELSE replay_prompts || jsonb_build_array(:prompt) END, "
                    "timeline = CASE WHEN status = :processing THEN timeline "
                    "ELSE timeline || CAST(:event AS jsonb) END "
                    "WHERE incident_id = :id AND status <> :resolved "
                    "AND workflow_id = :workflow_id AND status <> :ignored"
                ),
                {
                    "id": incident_id,
                    "workflow_id": workflow_id,
                    "status": IncidentStatus.PROCESSING.value,
                    "processing": IncidentStatus.PROCESSING.value,
                    "updated_at": now,
                    "prompt": replay_prompt,
                    "event": json.dumps([{"at": now.isoformat(), "event": IncidentEvent.PROCESSING.value}]),
                    "resolved": IncidentStatus.RESOLVED.value,
                    "ignored": IncidentStatus.IGNORED.value,
                },
            )
            return updated.rowcount == 1

    def mark_failed(self, incident_id: str, workflow_id: str, error: str) -> None:
        now = datetime.now(UTC)
        with self.database.sessions.begin() as session:
            session.execute(
                text(
                    "UPDATE incidents SET status = :status, updated_at = :updated_at, "
                    "diagnosis = jsonb_set(COALESCE(diagnosis, '{}'::jsonb), '{hypothesis}', to_jsonb(CAST(:hypothesis AS text))), "
                    "timeline = CASE WHEN status = :failed THEN timeline ELSE timeline || CAST(:event AS jsonb) END "
                    "WHERE incident_id = :id AND workflow_id = :workflow_id AND status NOT IN (:resolved, :ignored)"
                ),
                {
                    "id": incident_id,
                    "workflow_id": workflow_id,
                    "status": IncidentStatus.FAILED.value,
                    "failed": IncidentStatus.FAILED.value,
                    "resolved": IncidentStatus.RESOLVED.value,
                    "ignored": IncidentStatus.IGNORED.value,
                    "updated_at": now,
                    "hypothesis": f"The workflow failed: {error}.",
                    "event": json.dumps([{"at": now.isoformat(), "event": IncidentEvent.FAILED.value}]),
                },
            )

    def is_current(self, incident_id: str, workflow_id: str) -> bool:
        with self.database.sessions() as session:
            row = session.execute(
                text("SELECT status, workflow_id FROM incidents WHERE incident_id = :id"),
                {"id": incident_id},
            ).one_or_none()
        return bool(
            row
            and row.workflow_id == workflow_id
            and row.status not in {IncidentStatus.RESOLVED.value, IncidentStatus.IGNORED.value}
        )

    def resolve(self, incident_id: str, alert: dict) -> None:
        now = datetime.now(UTC)
        with self.database.sessions.begin() as session:
            session.execute(
                text(
                    """
                    INSERT INTO incidents (incident_id, status, alert, diagnosis, updated_at, timeline)
                    VALUES (:id, :status, CAST(:alert AS jsonb), CAST(:diagnosis AS jsonb),
                            :updated_at, CAST(:event AS jsonb))
                    ON CONFLICT (incident_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        alert = EXCLUDED.alert,
                        updated_at = EXCLUDED.updated_at,
                        timeline = incidents.timeline || EXCLUDED.timeline
                    """
                ),
                {
                    "id": incident_id,
                    "alert": json.dumps(alert),
                    "status": IncidentStatus.RESOLVED.value,
                    "diagnosis": json.dumps({}),
                    "updated_at": now,
                    "event": json.dumps([{"at": now.isoformat(), "event": IncidentEvent.RESOLVED.value}]),
                },
            )

    def save(self, incident: dict) -> None:
        now = datetime.now(UTC)
        with self.database.sessions.begin() as session:
            current = (
                session.execute(
                    text(
                        "SELECT status, alert, diagnosis, pr_url, workflow_id, diagnosis_history, timeline, attempts, replayed_at, replay_prompts, "
                        "manual_actions, audit_actions "
                        "FROM incidents WHERE incident_id = :id FOR UPDATE"
                    ),
                    {"id": incident["id"]},
                )
                .mappings()
                .one_or_none()
            )
            if current and (
                current["status"] == IncidentStatus.RESOLVED.value
                or current["status"] == IncidentStatus.IGNORED.value
                or current["workflow_id"] != incident.get("workflow_id")
                or (
                    current["status"] == incident.get("status")
                    and current["alert"] == incident.get("alert")
                    and current["diagnosis"] == incident.get("diagnosis", {})
                )
            ):
                return
            history = (current["diagnosis_history"] if current else []) or []
            timeline = (current["timeline"] if current else []) or []
            history.append({"at": now.isoformat(), "diagnosis": incident.get("diagnosis", {})})
            timeline.append({"at": now.isoformat(), "event": incident.get("status", "updated")})
            values = {
                "id": incident["id"],
                "workflow_id": incident.get("workflow_id", (current["workflow_id"] if current else None)),
                "status": incident["status"],
                "alert": json.dumps(incident["alert"]),
                "diagnosis": json.dumps(incident.get("diagnosis", {})),
                "pr_url": incident.get("pull_request_url", (current["pr_url"] if current else None)),
                "attempts": incident.get("attempts", (current["attempts"] if current else 0) or 0),
                "updated_at": now,
                "replayed_at": incident.get("replayed_at", (current["replayed_at"] if current else None)),
                "replay_prompts": json.dumps(
                    incident.get("replay_prompts", (current["replay_prompts"] if current else []) or [])
                ),
                "manual_actions": json.dumps(
                    incident.get("manual_actions", (current["manual_actions"] if current else []) or [])
                ),
                "audit_actions": json.dumps(
                    incident.get("audit_actions", (current["audit_actions"] if current else []) or [])
                ),
                "history": json.dumps(history),
                "timeline": json.dumps(timeline),
            }
            session.execute(
                text(
                    """
                    INSERT INTO incidents (incident_id, workflow_id, status, alert, diagnosis, pr_url, attempts, updated_at,
                                           replayed_at, replay_prompts, manual_actions, diagnosis_history, timeline,
                                           audit_actions)
                    VALUES (:id, :workflow_id, :status, CAST(:alert AS jsonb), CAST(:diagnosis AS jsonb), :pr_url, :attempts,
                            :updated_at, :replayed_at, CAST(:replay_prompts AS jsonb), CAST(:manual_actions AS jsonb),
                            CAST(:history AS jsonb), CAST(:timeline AS jsonb), CAST(:audit_actions AS jsonb))
                    ON CONFLICT (incident_id) DO UPDATE SET
                        workflow_id = EXCLUDED.workflow_id, status = EXCLUDED.status, alert = EXCLUDED.alert, diagnosis = EXCLUDED.diagnosis,
                        pr_url = EXCLUDED.pr_url, attempts = EXCLUDED.attempts, updated_at = EXCLUDED.updated_at,
                        replayed_at = EXCLUDED.replayed_at, replay_prompts = EXCLUDED.replay_prompts,
                        manual_actions = EXCLUDED.manual_actions, diagnosis_history = EXCLUDED.diagnosis_history,
                        timeline = EXCLUDED.timeline, audit_actions = EXCLUDED.audit_actions
                    """
                ),
                values,
            )

    def record_manual_action(self, incident_id: str, result: dict) -> None:
        now = datetime.now(UTC)
        with self.database.sessions.begin() as session:
            updated = session.execute(
                text(
                    "UPDATE incidents SET manual_actions = manual_actions || CAST(:action AS jsonb), "
                    "status = CASE WHEN :action_status = :succeeded THEN :pending ELSE status END, "
                    "updated_at = :updated_at, timeline = timeline || CAST(:event AS jsonb) "
                    "WHERE incident_id = :id"
                ),
                {
                    "id": incident_id,
                    "action": json.dumps([{**result, "at": now.isoformat()}]),
                    "action_status": result.get("status", ""),
                    "succeeded": ActionStatus.SUCCEEDED.value,
                    "pending": IncidentStatus.PENDING.value,
                    "updated_at": now,
                    "event": json.dumps([{"at": now.isoformat(), "event": IncidentEvent.MANUAL_ACTION_EXECUTED.value}]),
                },
            )
            if updated.rowcount != 1:
                raise LookupError(f"incident not found: {incident_id}")

    def ignore(self, incident_id: str) -> None:
        now = datetime.now(UTC)
        with self.database.sessions.begin() as session:
            updated = session.execute(
                text(
                    "UPDATE incidents SET status = :status, updated_at = :updated_at, "
                    "timeline = timeline || CAST(:event AS jsonb) WHERE incident_id = :id"
                ),
                {
                    "id": incident_id,
                    "status": IncidentStatus.IGNORED.value,
                    "updated_at": now,
                    "event": json.dumps([{"at": now.isoformat(), "event": IncidentEvent.IGNORED.value}]),
                },
            )
            if updated.rowcount != 1:
                raise LookupError(f"incident not found: {incident_id}")

    def delete(self, incident_id: str) -> None:
        with self.database.sessions.begin() as session:
            deleted = session.execute(text("DELETE FROM incidents WHERE incident_id = :id"), {"id": incident_id})
            if deleted.rowcount != 1:
                raise LookupError(f"incident not found: {incident_id}")

    def list(self, limit: int = 200, source: str | None = None, status: str | None = None) -> list[dict]:
        clauses = []
        params: dict[str, object] = {"limit": limit}
        if source:
            clauses.append("alert->'labels'->>'source' = :source")
            params["source"] = source
        if status:
            clauses.append("status = :status")
            params["status"] = status
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        statement = text(
            f"""
            SELECT incident_id, workflow_id, status, alert, diagnosis, pr_url, attempts, updated_at,
                   replayed_at, replay_prompts, manual_actions, diagnosis_history, timeline, audit_actions
            FROM incidents {where}
            ORDER BY updated_at DESC, incident_id ASC
            LIMIT :limit
            """
        )
        with self.database.sessions() as session:
            return [self._as_dict(row) for row in session.execute(statement, params).mappings()]

    def get(self, incident_id: str) -> dict | None:
        statement = text(
            """
            SELECT incident_id, workflow_id, status, alert, diagnosis, pr_url, attempts, updated_at,
                   replayed_at, replay_prompts, manual_actions, diagnosis_history, timeline, audit_actions
            FROM incidents WHERE incident_id = :incident_id
            """
        )
        with self.database.sessions() as session:
            row = session.execute(statement, {"incident_id": incident_id}).mappings().one_or_none()
        return self._as_dict(row) if row else None

    @staticmethod
    def _as_dict(row) -> dict:
        def value(name: str):
            item = row[name]
            return json.loads(item) if isinstance(item, str) else item

        return {
            "id": row["incident_id"],
            "workflow_id": row["workflow_id"],
            "status": row["status"],
            "alert": value("alert"),
            "diagnosis": value("diagnosis"),
            "pull_request_url": row["pr_url"],
            "attempts": row["attempts"],
            "updated_at": row["updated_at"].isoformat(),
            "replayed_at": row["replayed_at"].isoformat() if row["replayed_at"] else None,
            "replay_prompts": value("replay_prompts") or [],
            "manual_actions": value("manual_actions") or [],
            "diagnosis_history": value("diagnosis_history") or [],
            "timeline": value("timeline") or [],
            "audit_actions": value("audit_actions") or [],
        }
