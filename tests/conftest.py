"""Fixtures compartilhadas para todos os testes."""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.database import Base
from app.main import app
from app.api.deps import get_db, get_chat_service
from app.services.chat import ChatService
from app.services.sentiment import LeiaSentimentAnalyzer


# ── Banco em memória para testes ──────────────────────────────

@pytest.fixture(scope="function")
def db_session():
    """Cria um banco SQLite em memória novo para cada teste."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ── Analisador mockado para não depender do LeIA real ─────────

@pytest.fixture
def mock_analyzer():
    """Retorna um SentimentAnalyzer que sempre classifica como Neutro."""
    analyzer = MagicMock()
    analyzer.analyze.return_value = {"Positivo": 0, "Negativo": 0, "Neutro": 1}
    return analyzer


# ── Extrator de tópicos mockado ───────────────────────────────

@pytest.fixture
def mock_topic_extractor():
    """Retorna um TopicExtractor mockado."""
    extractor = MagicMock()
    extractor.extract.return_value = [
        {"term": "live", "score": 0.95},
        {"term": "incrivel", "score": 0.72},
    ]
    return extractor


# ── Cliente HTTP para testes de rota ──────────────────────────

@pytest.fixture
def client(db_session, mock_analyzer, mock_topic_extractor):
    """Cliente de teste com dependências sobrescritas."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_chat_service():
        return ChatService(db_session, mock_analyzer, mock_topic_extractor)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_chat_service] = override_get_chat_service

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ── Cliente autenticado ──────────────────────────────────────

@pytest.fixture
def auth_client(client):
    """Cliente autenticado com token JWT."""
    client.post("/api/auth/register", json={
        "email": "auth@test.com",
        "name": "Auth User",
        "password": "testpass123",
    })
    login_resp = client.post("/api/auth/login", json={
        "email": "auth@test.com",
        "password": "testpass123",
    })
    token = login_resp.json()["access_token"]
    client.headers = {"Authorization": f"Bearer {token}"}
    return client
