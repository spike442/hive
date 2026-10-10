from datetime import timedelta

from core.domain import AgentDomain
from core.orchestration import ActivityName, WorkflowType
from temporalio import workflow
from temporalio.common import RetryPolicy, WorkflowIDReusePolicy
from temporalio.workflow import ParentClosePolicy


@workflow.defn(name=WorkflowType.PR_REVIEW.value)
class PullRequestReviewWorkflow:
    @workflow.run
    async def run(self, request: dict) -> dict | None:
        request["workflow_id"] = workflow.info().workflow_id
        if not await workflow.execute_activity(
            ActivityName.AGENT_IS_ACTIVE.value,
            AgentDomain.PULL_REQUEST_REVIEW.value,
            task_queue=workflow.info().task_queue,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=RetryPolicy(maximum_attempts=3),
        ):
            return None

        claimed = await workflow.execute_activity(
            ActivityName.PR_CLAIM.value,
            request,
            task_queue=workflow.info().task_queue,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=5),
        )
        if not claimed:
            return None

        try:
            request = await workflow.execute_activity(
                ActivityName.PR_PREPARE.value,
                request,
                task_queue=workflow.info().task_queue,
                start_to_close_timeout=timedelta(minutes=10),
                schedule_to_close_timeout=timedelta(minutes=20),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            result = await workflow.execute_activity(
                ActivityName.PR_REVIEW.value,
                request,
                task_queue=request["agent_task_queue"],
                start_to_close_timeout=timedelta(minutes=60),
                schedule_to_close_timeout=timedelta(hours=3),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=10),
                    maximum_interval=timedelta(minutes=2),
                    maximum_attempts=2,
                ),
            )

            if result.get("failure"):
                await workflow.execute_activity(
                    ActivityName.PR_FAIL.value,
                    {**request, **result, "error": result["failure"]},
                    task_queue=workflow.info().task_queue,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=5),
                )
                return result

            await workflow.execute_activity(
                ActivityName.PR_COMPLETE.value,
                {"workflow_id": workflow.info().workflow_id, "review": result},
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
                ActivityName.PR_FAIL.value,
                {**request, "error": type(error).__name__},
                task_queue=workflow.info().task_queue,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
            raise

        return result


@workflow.defn(name=WorkflowType.PR_REVIEW_POLL.value)
class PullRequestReviewPollWorkflow:
    @workflow.run
    async def run(self) -> int:
        requests = await workflow.execute_activity(
            ActivityName.PR_DISCOVER.value,
            task_queue=workflow.info().task_queue,
            start_to_close_timeout=timedelta(minutes=10),
            schedule_to_close_timeout=timedelta(minutes=20),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=10),
                maximum_interval=timedelta(minutes=2),
                maximum_attempts=3,
            ),
        )
        for request in requests:
            await workflow.execute_activity(
                ActivityName.PR_ACKNOWLEDGE.value,
                request,
                task_queue=workflow.info().task_queue,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
        if not await workflow.execute_activity(
            ActivityName.AGENT_IS_ACTIVE.value,
            AgentDomain.PULL_REQUEST_REVIEW.value,
            task_queue=workflow.info().task_queue,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=RetryPolicy(maximum_attempts=3),
        ):
            return len(requests)

        for request in requests:
            workflow_id = f"pr-review-{request['owner']}-{request['repository']}-{request['number']}-{workflow.uuid4()}"
            await workflow.start_child_workflow(
                PullRequestReviewWorkflow.run,
                request,
                id=workflow_id,
                task_queue=workflow.info().task_queue,
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
                parent_close_policy=ParentClosePolicy.ABANDON,
            )
        return len(requests)
