from datetime import timedelta

from core.domain import AgentDomain
from core.orchestration import ActivityName, WorkflowType
from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn(name=WorkflowType.SRE_INCIDENT.value)
class SreIncidentWorkflow:
    @workflow.run
    async def run(self, request: dict) -> dict:
        request["workflow_id"] = workflow.info().workflow_id
        if request["kind"] == "replay" and not await workflow.execute_activity(
            ActivityName.SRE_QUEUE_REPLAY.value,
            request,
            task_queue=workflow.info().task_queue,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=5),
        ):
            return {"status": "not_replayable"}

        active = await workflow.execute_activity(
            ActivityName.AGENT_IS_ACTIVE.value,
            AgentDomain.SRE.value,
            task_queue=workflow.info().task_queue,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        if not active:
            return {"status": "acknowledged"}

        processing = await workflow.execute_activity(
            ActivityName.SRE_MARK_PROCESSING.value,
            request,
            task_queue=workflow.info().task_queue,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=5),
        )
        if not processing:
            return {"status": "resolved"}
        try:
            request["rag_context"] = await workflow.execute_activity(
                ActivityName.SRE_RAG_CONTEXT.value,
                request,
                task_queue=workflow.info().task_queue,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            result = await workflow.execute_activity(
                ActivityName.SRE_INVESTIGATE.value,
                request,
                task_queue=request["agent_task_queue"],
                start_to_close_timeout=timedelta(minutes=45),
                schedule_to_close_timeout=timedelta(hours=2),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=10),
                    maximum_interval=timedelta(minutes=2),
                    maximum_attempts=2,
                ),
            )
            await workflow.execute_activity(
                ActivityName.SRE_COMPLETE.value,
                {"workflow_id": workflow.info().workflow_id, "incident": result},
                task_queue=workflow.info().task_queue,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(minutes=1),
                    maximum_attempts=5,
                ),
            )
        except Exception as error:
            await workflow.execute_activity(
                ActivityName.SRE_FAIL.value,
                {**request, "error": type(error).__name__},
                task_queue=workflow.info().task_queue,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
            raise
        return result


@workflow.defn(name=WorkflowType.MANUAL_ACTION.value)
class ManualActionWorkflow:
    @workflow.run
    async def run(self, request: dict) -> dict:
        request["workflow_id"] = workflow.info().workflow_id
        return await workflow.execute_activity(
            ActivityName.MANUAL_ACTION.value,
            request,
            task_queue=workflow.info().task_queue,
            start_to_close_timeout=timedelta(minutes=3),
            schedule_to_close_timeout=timedelta(minutes=3),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
