"""Testes para app/schemas/chat.py."""

import pytest
from pydantic import ValidationError
from app.schemas.chat import (
    ChatMessage,
    MessageResponse,
    WordFrequencyItem,
    WordFrequencyResponse,
    SentimentResponse,
)


class TestChatMessage:
    def test_valid(self):
        msg = ChatMessage(live_id="abc", author="User", message="Hello")
        assert msg.live_id == "abc"
        assert msg.author == "User"
        assert msg.message == "Hello"

    def test_missing_field(self):
        with pytest.raises(ValidationError):
            ChatMessage(live_id="abc", author="User")  # sem message

    def test_empty_strings(self):
        msg = ChatMessage(live_id="", author="", message="")
        assert msg.live_id == ""


class TestWordFrequencyResponse:
    def test_items(self):
        items = [
            WordFrequencyItem(palavra="gato", frequencia=5),
            WordFrequencyItem(palavra="cachorro", frequencia=3),
        ]
        resp = WordFrequencyResponse(live_id="live1", word_frequency=items)
        assert resp.live_id == "live1"
        assert len(resp.word_frequency) == 2
        assert resp.word_frequency[0].palavra == "gato"


class TestSentimentResponse:
    def test_valid(self):
        resp = SentimentResponse(
            live_id="live1",
            total_messages_analyzed=10,
            sentiment_summary={"Positivo": 5, "Negativo": 2, "Neutro": 3},
            library_used="LeIA",
            model="LeIA (VADER adaptado para português)",
        )
        assert resp.live_id == "live1"
        assert resp.total_messages_analyzed == 10
