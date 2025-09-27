from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.core.config import settings
from app.infrastructure.database import Base, engine
from app.infrastructure.ml import get_sentiment_pipeline


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url=settings.DOCS_URL,
        redoc_url=settings.REDOC_URL,
        openapi_url=settings.OPENAPI_URL,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    app.include_router(chat_router, prefix=settings.API_PREFIX)

    @app.get("/", tags=["healthcheck"])
    async def healthcheck():
        return {"status": "online"}

    return app


app = create_application()


# @app.on_event("startup")
# async def on_startup() -> None:
#     Base.metadata.create_all(bind=engine)
#     # Carrega o pipeline de sentimento uma única vez na inicialização.
#     get_sentiment_pipeline()