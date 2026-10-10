from pathlib import Path

from core.observability.health import workers_running
from core.package.version import package_version
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from hive.bootstrap.lifespan import application_lifespan
from hive.domains.pr_review.api import router as pr_review_router
from hive.domains.sre.api import router as sre_router
from hive.web.api import router as agents_router
from hive.web.cors import ConfiguredCORSMiddleware


def create_app() -> FastAPI:
    application = FastAPI(title="Hive", version=package_version("hive"), lifespan=application_lifespan)

    def allowed_origins(request):
        return request.app.state.runtime.settings.api.allowed_origins

    application.add_middleware(
        ConfiguredCORSMiddleware,
        allowed_origins=allowed_origins,
        methods=("GET", "POST", "DELETE", "OPTIONS"),
        allowed_headers=("Authorization", "Content-Type"),
    )

    @application.get("/healthz")
    @application.get("/readyz")
    def healthz() -> dict[str, str]:
        if not workers_running(getattr(application.state, "worker_tasks", ())):
            raise HTTPException(status_code=503, detail="Hive background worker stopped")
        return {"status": "ok", "version": package_version("hive")}

    @application.get("/version")
    def version() -> dict[str, str]:
        return {"version": package_version("hive")}

    @application.get("/config")
    def config() -> dict[str, str]:
        return application.state.runtime.settings.ui.model_dump()

    application.include_router(agents_router)
    application.include_router(sre_router)
    application.include_router(pr_review_router)
    static_dir = Path(__file__).resolve().parents[2] / "ui" / "dist"
    if static_dir.is_dir():
        application.mount("/", StaticFiles(directory=static_dir, html=True), name="ui")
    return application


app = create_app()
