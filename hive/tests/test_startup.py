import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import hive.server as server


def test_app_starts(monkeypatch):
    settings = SimpleNamespace(
        api=SimpleNamespace(allowed_origins=[]),
        ui=SimpleNamespace(),
        control_token="test-token",
    )

    runtime = SimpleNamespace(settings=settings, agent_service=object(), agents={})

    @asynccontextmanager
    async def fake_lifespan(application):
        application.state.runtime = runtime
        yield

    monkeypatch.setattr(server, "application_lifespan", fake_lifespan)
    application = server.create_app()

    async def exercise_lifespan() -> None:
        async with application.router.lifespan_context(application):
            assert application.state.runtime.settings is settings
            assert application.state.runtime.agent_service is not None

    asyncio.run(exercise_lifespan())
