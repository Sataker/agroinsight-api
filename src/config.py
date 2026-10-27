from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://agroinsight:password@localhost:5432/agroinsight"

    # Auth
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24h

    # Claude API
    anthropic_api_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # WhatsApp / n8n
    n8n_webhook_url: str = ""
    uazapi_base_url: str = ""
    uazapi_token: str = ""
    uazapi_instance: str = ""

    # Comma-separated list of origins allowed to call the API (the Next.js dashboard)
    cors_origins: str = "http://localhost:3000,http://localhost:3200"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    env: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.env != "development" and settings.jwt_secret == "change-me":
        raise RuntimeError("JWT_SECRET must be set outside development")
    return settings
