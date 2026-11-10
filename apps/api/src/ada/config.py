from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Finds the repo-root .env whether you start the API from the repo root or from apps/api
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")
    app_env: str = "dev"
    region: str = "IN"            # change this to add a country (plus an adapter)
    language: str = "en"
    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"
    decision_provider: str = "rules"   # rules | claude | jev
    escalation_threshold: float = 0.6
    run_spend_cap_usd: float = 5.0
    youtube_api_key: str = ""
    anthropic_api_key: str = ""
    jev_api_key: str = ""
    jev_base_url: str = ""
    # Task queue: the model machine polls /api/v1/taskoutput with this bearer key.
    # Blank = the worker endpoints answer 503 (queue off). Use 32+ random characters.
    task_worker_key: str = ""
    task_lease_seconds: int = 900       # a claimed task goes back to the queue after this
    task_max_attempts: int = 3          # claims before a task is marked failed
    task_expire_minutes: int = 30       # still unfinished after this = failed (worker offline?)
    task_max_pending_per_user: int = 3  # unfinished tasks one user can have at a time
    task_keep_days: int = 7             # finished tasks are deleted after this
    sentry_dsn: str = ""
    jwt_secret: str = "dev-only-change-me"
    session_minutes: int = 60 * 24 * 7
    reset_minutes: int = 30
    frontend_url: str = "http://localhost:5173"
    mail_provider: str = "console"   # console (prints to log) | smtp
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    mail_from: str = ""              # e.g. "Ad Campaign Analyser <you@gmail.com>"
    web_dist: str = ""               # built website folder; set in the production image only

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, v: str) -> str:
        """Hosts (Neon, Render) hand out postgres:// URLs; SQLAlchemy needs the psycopg driver."""
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v


settings = Settings()
