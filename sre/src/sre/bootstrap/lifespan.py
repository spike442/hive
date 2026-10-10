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

from sre.bootstrap.runtime import build_runtime
from sre.infrastructure.config import Settings
from sre.worker import SreActivities

logger = logging.getLogger(__name__)


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = Settings.load()
    configure_logging(settings.logging.level)
    runtime = build_runtime(settings)
    client = await Client.connect(settings.temporal.address, namespace=settings.temporal.namespace)
    activities = SreActivities(runtime)
    activity_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="sre-activity")
    worker = Worker(
        client,
        task_queue=settings.temporal.task_queue,
        activities=[activities.investigate],
        activity_executor=activity_executor,
        max_concurrent_activities=8,
        graceful_shutdown_timeout=timedelta(seconds=240),
    )
    application.state.runtime = runtime

    task = asyncio.create_task(worker.run())
    application.state.worker_tasks = [task]
    logger.info("SRE loaded version=%s", package_version("sre"))
    try:
        yield
    finally:
        await worker.shutdown()
        await asyncio.gather(task, return_exceptions=True)
        activity_executor.shutdown(wait=True)
        runtime.diagnosis.close()
        await client.service_client.close()


__all__ = ["application_lifespan"]
