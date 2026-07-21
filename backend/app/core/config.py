from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI-Assisted Workflow Builder API"
    app_version: str = "0.1.0"
    environment: str = "development"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "workflow_builder"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_enabled: bool = False
    rate_limit_fail_open: bool = True

    openai_api_key: str = ""
    openai_model: str = "gpt-5.4-nano"

    jwt_secret_key: str = "change-me-in-production-with-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30


settings = Settings()
