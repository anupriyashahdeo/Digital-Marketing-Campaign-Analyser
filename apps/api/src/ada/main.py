from fastapi import FastAPI

from ada.api.v1 import auth, events, imports, runs
from ada.config import settings
from ada.db.models import Base
from ada.db.session import engine
from ada.observability.setup import init


def create_app() -> FastAPI:
    init()
    if settings.app_env == "prod" and settings.jwt_secret == "dev-only-change-me":
        raise RuntimeError("Set JWT_SECRET before running in production")
    if settings.app_env == "dev":
        Base.metadata.create_all(engine)   # production uses Alembic migrations instead
    app = FastAPI(title="Ad Campaign Analyser", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "region": settings.region, "env": settings.app_env}

    for r in (auth.router, runs.router, events.router, imports.router):
        app.include_router(r, prefix="/api/v1")
    return app


app = create_app()
