from core.domain import AlertSource
from core.orchestration import ActivityName
from temporalio import activity

from sre.application.alerts import process_alert_payload
from sre.application.replay import replay_incident
from sre.bootstrap.runtime import Runtime


class SreActivities:
    def __init__(self, runtime: Runtime):
        self.runtime = runtime

    @activity.defn(name=ActivityName.SRE_INVESTIGATE.value)
    def investigate(self, request: dict) -> dict:
        if request["kind"] == "replay":
            return replay_incident(
                self.runtime,
                request["incident_id"],
                request["prompt"],
                request["incident"],
                request["rag_context"],
            )

        alert = request["alert"]
        source = AlertSource(alert["labels"]["source"])
        return process_alert_payload(
            self.runtime,
            {"alerts": [alert]},
            source,
            request["rag_context"],
        )[0]
