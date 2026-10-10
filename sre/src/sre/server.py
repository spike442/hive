from core.observability.health import workers_running
from core.package.version import package_version
from fastapi import FastAPI, HTTPException

from sre.bootstrap.lifespan import application_lifespan


def create_app() -> FastAPI:
    application = FastAPI(title="SRE SRE agent", lifespan=application_lifespan)

    @application.get("/healthz")
    @application.get("/readyz")
    def healthz() -> dict[str, str]:
        if not workers_running(getattr(application.state, "worker_tasks", ())):
            raise HTTPException(status_code=503, detail="Temporal worker stopped")
        return {"status": "ok", "version": package_version("sre")}

    return application


app = create_app()
