"""Testes para app/services/chat.py e app/services/sentiment.py."""

from app.services.chat import ChatService


def test_save_message(db_session, mock_analyzer):
    svc = ChatService(db_session, mock_analyzer)
    msg = svc.save_message("live1", "User", "Hello world")
    assert msg.live_id == "live1"
    assert msg.message == "Hello world"


def test_word_frequency(db_session, mock_analyzer):
    svc = ChatService(db_session, mock_analyzer)
    svc.save_message("live1", "A", "cachorro gato passarinho")
    svc.save_message("live1", "B", "cachorro papagaio")

    freq = svc.word_frequency("live1", top_n=3)
    assert freq is not None
    assert freq[0][0] == "cachorro"  # palavra mais frequente
    assert freq[0][1] == 2


def test_word_frequency_stopwords_removed(db_session, mock_analyzer):
    """Verifica que stopwords em português são removidas."""
    svc = ChatService(db_session, mock_analyzer)
    svc.save_message("live1", "A", "eu e tu gostamos do cachorro")

    freq = svc.word_frequency("live1", top_n=10)
    words = [w for w, _ in freq]
    assert "eu" not in words
    assert "e" not in words
    assert "tu" not in words
    assert "do" not in words
    assert "gostamos" in words
    assert "cachorro" in words


def test_word_frequency_empty(db_session, mock_analyzer):
    svc = ChatService(db_session, mock_analyzer)
    freq = svc.word_frequency("nonexistent")
    assert freq is None


def test_sentiment_summary(db_session, mock_analyzer):
    svc = ChatService(db_session, mock_analyzer)
    svc.save_message("live1", "A", "Que live boa!")

    result = svc.sentiment_summary("live1")
    assert result["total_messages"] == 1
    assert result["model"] == "LeIA (VADER adaptado para português)"
    assert result["sentiments"] == {"Positivo": 0, "Negativo": 0, "Neutro": 1}


def test_sentiment_summary_empty(db_session, mock_analyzer):
    svc = ChatService(db_session, mock_analyzer)
    result = svc.sentiment_summary("vazia")
    assert result is None


# ── Testes do analisador real (LeIA) ──────────────────────────

from app.services.sentiment import LeiaSentimentAnalyzer


def test_leia_analyzer_positive():
    analyzer = LeiaSentimentAnalyzer()
    result = analyzer.analyze(["Que live maravilhosa! Incrível!"])
    assert result["Positivo"] >= 0
    assert result["Negativo"] >= 0
    assert result["Neutro"] >= 0
    assert sum(result.values()) == 1


def test_leia_analyzer_multiple():
    analyzer = LeiaSentimentAnalyzer()
    texts = [
        "Estou muito feliz!",
        "Que raiva disso!",
        "Ok, tanto faz."
    ]
    result = analyzer.analyze(texts)
    assert sum(result.values()) == 3
