from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "dev"
    region: str = "IN"            # change this to add a country (plus an adapter)
    language: str = "en"
    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"
    decision_provider: str = "rules"
    escalation_threshold: float = 0.6
    run_spend_cap_usd: float = 5.0
    youtube_api_key: str = ""
    anthropic_api_key: str = ""
    jev_api_key: str = ""
    jev_base_url: str = ""
    sentry_dsn: str = ""
    jwt_secret: str = "dev-only-change-me"
    session_minutes: int = 60 * 24 * 7
    reset_minutes: int = 30
    frontend_url: str = "http://localhost:5173"


settings = Settings()
