from core.observability.health import workers_running
from core.package.version import package_version
from fastapi import FastAPI, HTTPException

from pr_review.bootstrap.lifespan import application_lifespan


def create_app() -> FastAPI:
    application = FastAPI(title="PR Review", version=package_version("pr-review"), lifespan=application_lifespan)

    @application.get("/healthz")
    @application.get("/readyz")
    async def health() -> dict[str, str]:
        if not workers_running(getattr(application.state, "worker_tasks", ())):
            raise HTTPException(status_code=503, detail="Temporal worker stopped")
        return {"status": "ok", "version": package_version("pr-review")}

    return application


app = create_app()
