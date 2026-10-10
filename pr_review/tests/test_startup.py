import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from pr_review import server


def test_app_starts(monkeypatch):
    @asynccontextmanager
    async def fake_lifespan(application):
        application.state.runtime = SimpleNamespace(
            settings=SimpleNamespace(version="1.0.0"),
        )
        yield

    monkeypatch.setattr(server, "application_lifespan", fake_lifespan)
    application = server.create_app()

    async def exercise_lifespan() -> None:
        async with application.router.lifespan_context(application):
            assert application.state.runtime.settings.version == "1.0.0"

    asyncio.run(exercise_lifespan())
