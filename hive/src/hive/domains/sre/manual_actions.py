import subprocess
from typing import Any

from core.domain import ActionStatus

from hive.domains.sre.incident_repository import IncidentRepository
from hive.infrastructure.config import ExecutionConfig


class ManualActionService:
    """Execute an operator-approved action and persist its result in Hive."""

    def __init__(self, config: ExecutionConfig, incidents: IncidentRepository):
        self.config = config
        self.incidents = incidents

    def execute(self, incident_id: str, action_index: int) -> dict[str, Any]:
        incident = self.incidents.get(incident_id)
        if not incident:
            raise ValueError("incident does not exist")
        actions = incident.get("diagnosis", {}).get("manual_actions", [])
        if action_index < 0 or action_index >= len(actions):
            raise ValueError("manual action does not exist")
        action = actions[action_index]
        try:
            completed = subprocess.run(
                action["command"],
                shell=True,
                cwd=self.config.working_directory,
                capture_output=True,
                text=True,
                timeout=self.config.command_timeout_seconds,
                check=False,
            )
            output = {
                "exit_code": completed.returncode,
                "stdout": completed.stdout[-self.config.max_output_bytes :],
                "stderr": completed.stderr[-self.config.max_output_bytes :],
                "status": ActionStatus.SUCCEEDED.value if completed.returncode == 0 else ActionStatus.FAILED.value,
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            output = {"status": ActionStatus.FAILED.value, "error": type(exc).__name__}
        result = {
            **action,
            **output,
            "action_index": action_index,
        }
        self.incidents.record_manual_action(incident_id, result)
        return result
