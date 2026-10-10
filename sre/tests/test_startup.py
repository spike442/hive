import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import sre.server as server


def test_application_starts(monkeypatch) -> None:
    @asynccontextmanager
    async def fake_lifespan(application):
        application.state.runtime = SimpleNamespace()
        worker = asyncio.create_task(asyncio.Event().wait())
        application.state.worker_tasks = [worker]
        try:
            yield
        finally:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)

    monkeypatch.setattr(server, "application_lifespan", fake_lifespan)
    application = server.create_app()
    health_route = next(route for route in application.routes if route.path == "/healthz")

    async def exercise_lifespan() -> None:
        async with application.router.lifespan_context(application):
            assert health_route.endpoint() == {"status": "ok", "version": "1.0.0"}

    asyncio.run(exercise_lifespan())
