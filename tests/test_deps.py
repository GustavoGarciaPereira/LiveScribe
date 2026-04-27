"""Testes para app/api/deps.py."""

from app.api.deps import get_chat_service
from app.services.sentiment import LeiaSentimentAnalyzer


def test_get_chat_service_returns_chat_service(db_session):
    service = get_chat_service(db_session)
    assert service is not None
    assert isinstance(service.sentiment_analyzer, LeiaSentimentAnalyzer)
