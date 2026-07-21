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

    CORS_ALLOW_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:5173",           # Vite / frontend dev
            "https://www.youtube.com",         # Extensão Chrome
            "https://m.youtube.com",           # YouTube mobile
        ]
    )
    CORS_ALLOW_CREDENTIALS: bool = False
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
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/callback/google"

    # YouTube Data API (obrigatório — defina no .env)
    YOUTUBE_API_KEY: str = ""

    @model_validator(mode="after")
    def _validate_secret_key(self):
        """Exige SECRET_KEY segura em qualquer ambiente que não seja dev local."""
        if self.SECRET_KEY == "change-me-in-production":
            if self.ENVIRONMENT == "development":
                import warnings
                warnings.warn(
                    "SECRET_KEY está com o valor padrão. Defina SECRET_KEY no .env "
                    "antes de qualquer deploy.",
                    stacklevel=2,
                )
            else:
                raise ValueError(
                    "SECRET_KEY deve ser configurado com um valor seguro. "
                    "Defina a variável SECRET_KEY no .env ou no ambiente."
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()