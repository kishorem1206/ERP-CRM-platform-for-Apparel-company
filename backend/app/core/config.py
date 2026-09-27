from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

# Look for .env in: current dir → parent dir (project root when running from backend/)
_env_candidates = [Path(".env"), Path("../.env"), Path(__file__).parents[3] / ".env"]
_env_file = next((str(p) for p in _env_candidates if p.exists()), ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_file, extra="ignore")

    # Application
    APP_ENV: Literal["development", "production"] = "development"
    APP_SECRET_KEY: str
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "apparel_erp"
    POSTGRES_USER: str = "erp_user"
    POSTGRES_PASSWORD: str

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # AI — OpenAI-compatible endpoint
    LLM_PROVIDER: str = ""
    LLM_API_KEY: str = ""
    LLM_API_BASE_URL: str = ""      # e.g. https://api.groq.com/openai/v1
    LLM_BASE_URL: str = ""          # alias — LLM_API_BASE_URL takes precedence
    LLM_MODEL: str = "openai/gpt-oss-20b"
    LLM_MAX_TOKENS: int = 10000
    LLM_TEMPERATURE: float = 0.3
    AGENT_ENABLE_CONFIRMATION: bool = True

    # Legacy keys — kept for backward compat
    GPTOSS120B_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    @property
    def effective_llm_api_key(self) -> str:
        return self.LLM_API_KEY or self.GPTOSS120B_API_KEY or self.ANTHROPIC_API_KEY

    @property
    def effective_llm_base_url(self) -> str:
        return self.LLM_API_BASE_URL or self.LLM_BASE_URL or ""

    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_LOCAL_PATH: str = "/media"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: str = ""

    # Observability
    SENTRY_DSN: str = ""

    # Rate limiting
    RATE_LIMIT_LOGIN: str = "5/15minute"
    RATE_LIMIT_API: str = "300/minute"
    RATE_LIMIT_AGENT: str = "30/minute"

    # WhatsApp Business Cloud API
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "change-me-whatsapp-verify-token"

    # Company defaults
    DEFAULT_CURRENCY: str = "INR"
    DEFAULT_HSN: str = "6111"
    COMPANY_STATE_CODE: int = 29

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


settings = Settings()
