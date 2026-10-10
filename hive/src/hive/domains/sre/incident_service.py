import logging
import re
from typing import Any

from core.domain import DiagnosisStatus, IncidentStatus

from hive.domains.sre.workspace import IncidentWorkspace
from hive.infrastructure.config import Settings
from hive.integrations.github import GitHubGateway

logger = logging.getLogger(__name__)


class IncidentService:
    """Apply SRE's validated incident decision and open its pull request."""

    def __init__(self, settings: Settings, github: GitHubGateway):
        self.settings = settings
        self.github = github
        self.target_repository = self._repository()
        self.workspace = IncidentWorkspace(self.target_repository, settings.incident)

    def apply(self, incident: dict[str, Any]) -> dict[str, Any]:
        if incident.get("status") == IncidentStatus.RESOLVED.value:
            return incident
        diagnosis = incident.get("diagnosis") or {}
        changes = diagnosis.get("proposed_changes") or []
        if not self._valid_change(diagnosis, changes):
            incident["status"] = IncidentStatus.BLOCKED.value
            return incident
        try:
            labels = [f"confidence:{diagnosis['confidence']}", f"risk:{diagnosis['risk']}"]
            branch = self.workspace.branch_for(changes)
            if self.github.find_pull_request(self.target_repository, self.settings.incident.branch, branch) is None:
                self.workspace.push_changes(changes)
            incident["pull_request_url"] = self.github.create_pull_request(
                self.target_repository,
                self.settings.incident.branch,
                branch,
                changes[0]["title"],
                changes[0]["body"],
                labels,
            )
            incident["status"] = IncidentStatus.PR_CREATED.value
        except Exception as exc:
            incident["status"] = IncidentStatus.FAILED.value
            diagnosis["hypothesis"] = f"The incident fix could not be published: {type(exc).__name__}."
            logger.exception("incident fix failed incident_id=%s", incident.get("id"))
        return incident

    def _repository(self):
        for repository in self.settings.repositories:
            if repository.name == self.settings.incident.repository:
                return repository
        raise ValueError(f"incident repository is not configured: {self.settings.incident.repository}")

    def _valid_change(self, diagnosis: dict[str, Any], changes: list[dict[str, Any]]) -> bool:
        if not changes or diagnosis.get("status") != DiagnosisStatus.PROPOSED.value:
            return False
        if not diagnosis.get("validation") or not diagnosis.get("rollback") or not diagnosis.get("evidence"):
            return False
        secret_material = re.compile(
            "|".join(f"(?:{pattern})" for pattern in self.settings.incident.secret_material_patterns)
        )
        return all(not secret_material.search(str(change.get("content", ""))) for change in changes)
