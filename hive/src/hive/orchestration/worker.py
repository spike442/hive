from concurrent.futures import Executor
from datetime import timedelta

from hive.orchestration.agent_activities import AgentStatusActivities
from hive.orchestration.pr_review_workflows import PullRequestReviewPollWorkflow, PullRequestReviewWorkflow
from hive.orchestration.sre_workflows import ManualActionWorkflow, SreIncidentWorkflow
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleIntervalSpec,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleState,
    ScheduleUpdate,
)
from temporalio.worker import Worker


def build_worker(client: Client, task_queue: str, agent_service, agents: dict, activity_executor: Executor) -> Worker:
    activities = [AgentStatusActivities(agent_service).is_active]
    activities.extend(activity for agent in agents.values() for activity in agent.activities)
    return Worker(
        client,
        task_queue=task_queue,
        workflows=[
            SreIncidentWorkflow,
            PullRequestReviewWorkflow,
            PullRequestReviewPollWorkflow,
            ManualActionWorkflow,
        ],
        activities=activities,
        activity_executor=activity_executor,
        max_concurrent_activities=8,
        graceful_shutdown_timeout=timedelta(seconds=240),
    )


async def ensure_pr_review_schedule(client: Client, task_queue: str, interval_seconds: int) -> None:
    schedule = Schedule(
        action=ScheduleActionStartWorkflow(
            PullRequestReviewPollWorkflow.run,
            id="hive-pr-review-scan",
            task_queue=task_queue,
        ),
        spec=ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(seconds=interval_seconds))]),
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
        state=ScheduleState(note="Managed by Hive", paused=False),
    )
    try:
        await client.create_schedule("hive-pr-review-scan", schedule)
    except ScheduleAlreadyRunningError:
        handle = client.get_schedule_handle("hive-pr-review-scan")

        async def update(_input) -> ScheduleUpdate:
            return ScheduleUpdate(schedule=schedule)

        await handle.update(update)
