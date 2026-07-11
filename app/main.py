from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import inspect, text

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.reports import router as reports_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.deps import init_report_queue
from app.core.config import settings
from app.core.limiter import limiter
from app.infrastructure.database import Base, engine


def _migrate_legacy_db():
    """Adiciona colunas/tabelas ausentes em bancos legados."""
    inspector = inspect(engine)

    # Tabela users (Fase 3 + Fase 3.5)
    if not inspector.has_table("users"):
        with engine.connect() as conn:
            conn.execute(text(
                "CREATE TABLE users ("
                "id INTEGER NOT NULL, "
                "email VARCHAR(255) NOT NULL, "
                "name VARCHAR(255) NOT NULL, "
                "google_id VARCHAR(255), "
                "password_hash VARCHAR(255), "
                "provider VARCHAR(50) NOT NULL DEFAULT 'local', "
                "is_active BOOLEAN DEFAULT 1, "
                "created_at DATETIME NOT NULL, "
                "PRIMARY KEY (id), "
                "UNIQUE (email), "
                "UNIQUE (google_id)"
                ")"
            ))
            conn.commit()
    else:
        # Adiciona colunas novas da Feature 1.5 em bancos existentes
        user_columns = [c["name"] for c in inspector.get_columns("users")]
        if "password_hash" not in user_columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
                conn.commit()
        if "provider" not in user_columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN provider VARCHAR(50) NOT NULL DEFAULT 'local'"))
                conn.commit()
        if "is_active" not in user_columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                conn.commit()

    # Coluna platform (Fase 2)
    columns = [c["name"] for c in inspector.get_columns("messages")]
    if "platform" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE messages ADD COLUMN platform VARCHAR(50) NOT NULL DEFAULT 'youtube'"))
            conn.commit()

    # Coluna user_id (Fase 3)
    if "user_id" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE messages ADD COLUMN user_id INTEGER REFERENCES users(id)"))
            conn.commit()


def create_application() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(bind=engine)
        _migrate_legacy_db()
        report_queue = init_report_queue()
        report_queue.start()
        yield
        report_queue.stop()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url=settings.DOCS_URL,
        redoc_url=settings.REDOC_URL,
        openapi_url=settings.OPENAPI_URL,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    app.include_router(auth_router)
    app.include_router(chat_router, prefix=settings.API_PREFIX)
    app.include_router(reports_router, prefix=settings.API_PREFIX)
    app.include_router(webhooks_router, prefix=settings.API_PREFIX)

    # Serve arquivos estaticos (CSS, JS)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard():
        dashboard_html = (Path(__file__).parent / "templates" / "dashboard.html").read_text(encoding="utf-8")
        return dashboard_html

    @app.get("/landing", response_class=HTMLResponse)
    async def landing():
        landing_html = (Path(__file__).parent / "templates" / "landing.html").read_text(encoding="utf-8")
        return landing_html

    @app.get("/favicon.ico", response_class=HTMLResponse)
    async def favicon():
        svg = (Path(__file__).parent / "templates" / "favicon.svg").read_text(encoding="utf-8")
        return Response(content=svg, media_type="image/svg+xml")

    @app.get("/", tags=["healthcheck"])
    async def healthcheck():
        return {"status": "online"}

    return app


app = create_application()