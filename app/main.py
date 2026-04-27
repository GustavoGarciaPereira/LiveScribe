from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import inspect, text

from app.api.routes.chat import router as chat_router
from app.core.config import settings
from app.infrastructure.database import Base, engine


def _migrate_platform_column():
    """Adiciona a coluna 'platform' se ela não existir (bancos legados)."""
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("messages")]
    if "platform" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE messages ADD COLUMN platform VARCHAR(50) NOT NULL DEFAULT 'youtube'"))
            conn.commit()


def create_application() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(bind=engine)
        _migrate_platform_column()
        yield

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url=settings.DOCS_URL,
        redoc_url=settings.REDOC_URL,
        openapi_url=settings.OPENAPI_URL,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    app.include_router(chat_router, prefix=settings.API_PREFIX)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard():
        dashboard_html = (Path(__file__).parent / "templates" / "dashboard.html").read_text(encoding="utf-8")
        return dashboard_html

    @app.get("/", tags=["healthcheck"])
    async def healthcheck():
        return {"status": "online"}

    return app


app = create_application()