"""Application configuration using Pydantic Settings."""


from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    # Database
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "butterfly_dev"

    postgres_url: str = "postgresql+asyncpg://butterfly:butterfly@localhost:5432/butterfly"
    redis_url: str = "redis://localhost:6379/0"

    # External APIs
    fred_api_key: str | None = None
    news_api_key: str | None = None
    anthropic_api_key: str | None = None
    acled_api_key: str | None = None
    acled_email: str | None = None
    acled_password: str | None = None
    gemini_api_key: str | None = None
    mistral_api_key: str | None = None

    # Application
    debug: bool = True
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    secret_key: str = "dev-secret-key-change-in-prod"

    # Simulation
    max_agents: int = 500
    simulation_timeout_seconds: int = 300
    max_parallel_simulations: int = 3

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"


settings = Settings()
