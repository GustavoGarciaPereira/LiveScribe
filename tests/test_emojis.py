"""Testes para o servico de analise de emojis."""

from app.services.chat import ChatService
from app.services.emojis import RegexEmojiExtractor


def test_emojis_present(db_session, mock_analyzer, mock_topic_extractor):
    """Deve extrair e contar emojis corretamente."""
    extractor = RegexEmojiExtractor()
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor, emoji_extractor=extractor)
    svc.save_message("live1", "A", "Eu 😂 amo isso 😍")
    svc.save_message("live1", "B", "Tambem 😂")

    result = svc.emoji_analysis("live1", top_n=10)
    assert result is not None
    assert result["live_id"] == "live1"
    assert result["total_emojis"] == 3
    emojis = result["emojis"]
    assert len(emojis) == 2
    assert emojis[0]["emoji"] == "😂"
    assert emojis[0]["count"] == 2


def test_no_emojis(db_session, mock_analyzer, mock_topic_extractor):
    """Mensagens sem emojis devem retornar lista vazia."""
    extractor = RegexEmojiExtractor()
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor, emoji_extractor=extractor)
    svc.save_message("live1", "A", "So texto sem emoji")

    result = svc.emoji_analysis("live1", top_n=10)
    assert result is not None
    assert result["total_emojis"] == 0
    assert result["emojis"] == []


def test_empty_live(db_session, mock_analyzer, mock_topic_extractor):
    """Live sem mensagens deve retornar 404 (None)."""
    extractor = RegexEmojiExtractor()
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor, emoji_extractor=extractor)
    result = svc.emoji_analysis("vazia")
    assert result is None


def test_sentiment_mapping(db_session, mock_analyzer, mock_topic_extractor):
    """Deve mapear o sentimento correto de cada emoji."""
    extractor = RegexEmojiExtractor()
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor, emoji_extractor=extractor)
    svc.save_message("live1", "A", "😂😭😐")

    result = svc.emoji_analysis("live1", top_n=10)
    assert result is not None
    emojis = {e["emoji"]: e["sentiment"] for e in result["emojis"]}
    assert emojis.get("😂") == "Positivo"
    assert emojis.get("😭") == "Negativo"
    assert emojis.get("😐") == "Neutro"
