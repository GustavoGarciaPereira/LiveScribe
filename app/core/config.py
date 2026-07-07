from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    PROJECT_NAME: str = "Chat Analytics API"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    DOCS_URL: str | None = "/docs"
    REDOC_URL: str | None = "/redoc"
    OPENAPI_URL: str | None = "/openapi.json"

    CORS_ALLOW_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: list[str] = Field(default_factory=lambda: ["*"])

    # Fuso horário
    TIMEZONE: str = "America/Sao_Paulo"

    # Ambiente
    ENVIRONMENT: str = "development"

    # Autenticação
    SECRET_KEY: str = "change-me-in-production"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    @model_validator(mode="after")
    def _validate_secret_key_in_production(self):
        if self.ENVIRONMENT == "production" and self.SECRET_KEY == "change-me-in-production":
            raise ValueError(
                "SECRET_KEY must be set to a secure value in production. "
                "Do not use the default 'change-me-in-production'."
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()