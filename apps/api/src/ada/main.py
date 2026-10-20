from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ada.api.v1 import auth, runs, workspaces, youtube
from ada.config import settings
from ada.db.models import Base
from ada.db.session import engine
from ada.observability.setup import init

# ---------------------------------------------------------------------------
# STEP 1: login.  STEP 2 (active): workspaces, dashboard, start a run.
# YouTube explorer (active): keyword search / link lookup with public stats.
# Later steps are commented out below. See docs/ROADMAP.md for the order.
# ---------------------------------------------------------------------------
# STEP 3+: uncomment when you build CSV import / live events. Both must be moved under
# /workspaces/{workspace_id}/... and use workspace_member, like runs.py, before switching on.
# from ada.api.v1 import events, imports

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",          # API responses hold private workspace data
}


def create_app() -> FastAPI:
    init()
    if settings.app_env == "prod" and (settings.jwt_secret == "dev-only-change-me"
                                       or len(settings.jwt_secret) < 32):
        raise RuntimeError("Set JWT_SECRET (32+ random chars) before running in production")
    if settings.app_env == "dev":
        Base.metadata.create_all(engine)   # production uses Alembic migrations instead
    app = FastAPI(title="Ad Campaign Analyser", version="0.1.0",
                  # Don't publish the API map in production
                  docs_url=None if settings.app_env == "prod" else "/docs",
                  redoc_url=None, openapi_url=None if settings.app_env == "prod" else "/openapi.json")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        if request.url.path.startswith("/assets/"):   # hashed filenames, safe to cache forever
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        for k, v in SECURITY_HEADERS.items():
            resp.headers.setdefault(k, v)
        if settings.app_env == "prod":
            resp.headers.setdefault("Strict-Transport-Security",
                                    "max-age=63072000; includeSubDomains")
        return resp

    @app.get("/health")
    def health():
        return {"status": "ok", "region": settings.region, "env": settings.app_env}

    # Every router except /health and /auth checks sign-in inside its own dependencies
    # (current_user / workspace_member), so access rules sit next to the routes they guard.
    for r in (auth.router, workspaces.router, runs.router, youtube.router):
        app.include_router(r, prefix="/api/v1")
    if settings.web_dist:
        _serve_website(app, Path(settings.web_dist).resolve())
    return app


def _serve_website(app: FastAPI, dist: Path) -> None:
    """Production: the API also serves the built React app, so site and API share one URL."""
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def website(path: str):
        if path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
        f = (dist / path).resolve()
        if path and f.is_file() and f.is_relative_to(dist):
            return FileResponse(f)
        # Any other path is a page of the app (e.g. /youtube); React Router picks it up
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})


app = create_app()
