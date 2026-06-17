"""Application configuration management."""
from functools import lru_cache
from typing import Any

from pydantic import Field, PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "AI Product Analytics Copilot"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API
    API_V1_PREFIX: str = "/api/v1"
    API_TITLE: str = "Product Analytics Copilot API"
    API_DESCRIPTION: str = "AI-powered product analytics for autonomous business investigation"
    API_DOCS_URL: str | None = "/docs"  # Set to None in production
    API_REDOC_URL: str | None = "/redoc"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True

    # Auth
    SECRET_KEY: str = Field(default="dev-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "analytics_copilot"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_CACHE_TTL: int = 3600  # 1 hour in seconds
    REDIS_INVESTIGATION_TTL: int = 86400  # 24 hours

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # AI / Google Gemini
    GEMINI_API_KEY: str = Field(default="")        # Get free key: aistudio.google.com
    GEMINI_MODEL: str = "gemini-2.0-flash"          # Fast + free tier
    GEMINI_MAX_TOKENS: int = 8192
    GEMINI_TEMPERATURE: float = 0.1                 # Low = deterministic analytics

    # SQL Safety
    SQL_QUERY_TIMEOUT_MS: int = 30000  # 30 seconds
    SQL_MAX_ROWS: int = 10000  # Max rows returned per query
    SQL_MAX_QUERIES_PER_INVESTIGATION: int = 15

    # Analytics
    DEFAULT_RETENTION_PERIODS: int = 12  # Weeks of retention to calculate
    COHORT_SIZE_MIN: int = 50  # Minimum cohort size for statistical significance
    ANOMALY_DETECTION_THRESHOLD: float = 2.0  # Standard deviations

    # Memory
    MEMORY_SIMILARITY_THRESHOLD: float = 0.8
    MEMORY_MAX_INVESTIGATIONS_STORED: int = 1000
    MEMORY_VECTOR_DIMENSIONS: int = 1536

    # Observability
    ENABLE_METRICS: bool = True
    METRICS_PATH: str = "/metrics"
    SENTRY_DSN: str | None = None
    TRACE_SAMPLE_RATE: float = 0.1

    @model_validator(mode="after")
    def set_production_overrides(self) -> "Settings":
        """Apply production-specific overrides."""
        if self.ENVIRONMENT == "production":
            # Disable docs in production for security
            object.__setattr__(self, "API_DOCS_URL", None)
            object.__setattr__(self, "API_REDOC_URL", None)
            object.__setattr__(self, "DATABASE_ECHO", False)
        return self

    @property
    def DATABASE_URL(self) -> str:
        """Construct async database URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Construct sync database URL (for Alembic)."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()