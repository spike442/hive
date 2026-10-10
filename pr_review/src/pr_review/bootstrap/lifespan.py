import asyncio
import logging
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import timedelta

from core.observability.logging import configure_logging
from core.package.version import package_version
from fastapi import FastAPI
from temporalio.client import Client
from temporalio.worker import Worker

from pr_review.bootstrap.runtime import build_runtime
from pr_review.infrastructure.config import Settings
from pr_review.worker import PullRequestReviewActivities

logger = logging.getLogger(__name__)


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = Settings.load()
    configure_logging(settings.logging.level)
    runtime = build_runtime(settings)
    client = await Client.connect(settings.temporal.address, namespace=settings.temporal.namespace)
    activities = PullRequestReviewActivities(runtime.workflow)
    activity_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="pr-review-activity")
    worker = Worker(
        client,
        task_queue=settings.temporal.task_queue,
        activities=[activities.review],
        activity_executor=activity_executor,
        max_concurrent_activities=8,
        graceful_shutdown_timeout=timedelta(seconds=900),
    )
    application.state.runtime = runtime

    task = asyncio.create_task(worker.run())
    application.state.worker_tasks = [task]
    logger.info("PR Review loaded version=%s", package_version("pr-review"))
    try:
        yield
    finally:
        await worker.shutdown()
        await asyncio.gather(task, return_exceptions=True)
        activity_executor.shutdown(wait=True)
        runtime.workflow.engine.close()
        runtime.workflow.prompt_store.close()
        await client.service_client.close()


__all__ = ["application_lifespan"]
