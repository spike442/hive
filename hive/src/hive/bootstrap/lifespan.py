import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from core.domain import AgentDomain
from core.observability.logging import configure_logging
from core.package.version import package_version
from fastapi import FastAPI
from temporalio.client import Client
from temporalio.runtime import PrometheusConfig, TelemetryConfig
from temporalio.runtime import Runtime as TemporalRuntime

from hive.bootstrap.runtime import Runtime, build_runtime
from hive.infrastructure.config import Settings
from hive.orchestration.worker import ensure_pr_review_schedule

logger = logging.getLogger(__name__)


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = Settings.load()
    configure_logging(settings.logging.level)
    temporal_runtime = TemporalRuntime(
        telemetry=TelemetryConfig(
            metrics=PrometheusConfig(
                bind_address=settings.temporal.metrics_bind_address,
                unit_suffix=True,
                durations_as_seconds=True,
            )
        )
    )
    temporal = await Client.connect(
        settings.temporal.address,
        namespace=settings.temporal.namespace,
        runtime=temporal_runtime,
    )
    runtime: Runtime | None = None
    tasks: list[asyncio.Task] = []
    try:
        runtime = build_runtime(settings, temporal, asyncio.get_running_loop())
        review = runtime.agents.get(AgentDomain.PULL_REQUEST_REVIEW)
        if review is not None:
            await ensure_pr_review_schedule(
                temporal,
                settings.temporal.workflow_task_queue,
                review.config.job_interval_seconds,
            )

        tasks = [
            asyncio.create_task(runtime.temporal_worker.run(), name="temporal-workflows"),
            asyncio.create_task(runtime.agent_service.run(), name="agent-status"),
        ]
        if runtime.alert_ingress is not None:
            tasks.append(asyncio.create_task(asyncio.to_thread(runtime.alert_ingress.run), name="alert-ingress"))
        application.state.runtime = runtime
        application.state.worker_tasks = tasks
        logger.info("Hive ready version=%s agents=%s", package_version("hive"), len(runtime.agents))
        yield
    finally:
        if runtime is not None:
            if runtime.alert_ingress is not None:
                runtime.alert_ingress.stop()
            runtime.agent_service.stop()
            await runtime.temporal_worker.shutdown()
            await asyncio.gather(*tasks, return_exceptions=True)
            runtime.activity_executor.shutdown(wait=True)
            if runtime.alert_ingress is not None:
                runtime.alert_ingress.close()
            runtime.health.close()
            runtime.agent_service.close()
            if runtime.rag is not None:
                runtime.rag.close()
            runtime.database.close()
            runtime.github.close()
        await temporal.service_client.close()
