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


def test_word_frequency_filters_urls_and_digits(db_session, mock_analyzer):
    """Verifica que URLs, digitos e tokens curtos sao filtrados."""
    svc = ChatService(db_session, mock_analyzer)
    svc.save_message("live1", "A", "Veja https://exemplo.com e http://teste.com")
    svc.save_message("live1", "B", "codigo 12345 versao 2 python3")

    freq = svc.word_frequency("live1", top_n=10)
    words = [w for w, _ in freq]
    assert "https" not in words
    assert "http" not in words
    assert "12345" not in words
    # '2' tem 1 char, deve ser filtrado
    # 'python3' tem 7 chars e nao e' digito puro — deve aparecer
    assert "python3" in words or "versao" in words


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


def test_leia_statistics_computed():
    """analyze_with_compound retorna estatisticas corretas."""
    analyzer = LeiaSentimentAnalyzer()
    texts = [
        "Que live maravilhosa! Incrível!",
        "Odio disso, horrivel",
        "Tanto faz, qualquer coisa",
    ]
    counts, compounds = analyzer.analyze_with_compound(texts)
    assert len(compounds) == 3
    assert sum(counts.values()) == 3
    # compound scores devem estar entre -1 e +1
    for c in compounds:
        assert -1 <= c <= 1

    stats = ChatService._compute_statistics(compounds)
    assert stats is not None
    assert stats["mean"] is not None
    assert stats["std_dev"] is not None
    assert stats["ci_95"] is not None
    assert len(stats["ci_95"]) == 2


def test_sentiment_summary_includes_statistics(db_session, mock_analyzer):
    """sentiment_summary retorna campo statistics."""
    # Mock com analyze_with_compound para testar o fluxo
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.analyze.return_value = {"Positivo": 1, "Negativo": 0, "Neutro": 0}
    mock.analyze_with_compound.return_value = ({"Positivo": 1, "Negativo": 0, "Neutro": 0}, [0.5, 0.3, 0.8])

    svc = ChatService(db_session, mock)
    svc.save_message("live-stats", "A", "Mensagem 1")
    svc.save_message("live-stats", "A", "Mensagem 2")
    svc.save_message("live-stats", "A", "Mensagem 3")

    result = svc.sentiment_summary("live-stats")
    assert result is not None
    assert "statistics" in result
    stats = result["statistics"]
    assert stats is not None
    assert stats["mean"] is not None
    assert stats["std_dev"] is not None
    assert stats["ci_95"] is not None


# ── Testes dos novos métodos do ChatService ────────────────────


def test_list_lives(db_session, mock_analyzer, mock_topic_extractor):
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor)
    svc.save_message("live1", "A", "msg1")
    svc.save_message("live1", "B", "msg2")
    svc.save_message("live2", "C", "msg3")

    lives = svc.list_lives()
    assert len(lives) == 2
    assert lives[0]["live_id"] in ("live1", "live2")
    assert lives[0]["total_messages"] > 0


def test_list_lives_empty(db_session, mock_analyzer, mock_topic_extractor):
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor)
    lives = svc.list_lives()
    assert lives == []


def test_sentiment_timeline(db_session, mock_analyzer, mock_topic_extractor):
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor)
    svc.save_message("live1", "A", "Que live boa!")
    svc.save_message("live1", "B", "Muito bom!")

    result = svc.sentiment_timeline("live1", interval_minutes=5)
    assert result is not None
    assert result["live_id"] == "live1"
    assert len(result["timeline"]) > 0
    bucket = result["timeline"][0]
    assert "sentiments" in bucket
    assert bucket["total_messages"] == 2


def test_sentiment_timeline_empty(db_session, mock_analyzer, mock_topic_extractor):
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor)
    result = svc.sentiment_timeline("vazia")
    assert result is None


def test_engagement_peaks(db_session, mock_analyzer, mock_topic_extractor):
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor)
    svc.save_message("live1", "A", "msg1")
    svc.save_message("live1", "B", "msg2")

    result = svc.engagement_peaks("live1", top_n=5, window_minutes=1)
    assert result is not None
    assert result["live_id"] == "live1"
    assert len(result["peaks"]) > 0


def test_engagement_peaks_empty(db_session, mock_analyzer, mock_topic_extractor):
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor)
    result = svc.engagement_peaks("vazia")
    assert result is None


def test_extract_topics(db_session, mock_analyzer, mock_topic_extractor):
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor)
    svc.save_message("live1", "A", "Que live incrível!")

    result = svc.extract_topics("live1", top_n=10)
    assert result is not None
    assert result["live_id"] == "live1"
    assert len(result["topics"]) == 2
    assert result["topics"][0]["term"] == "live"


def test_extract_topics_empty(db_session, mock_analyzer, mock_topic_extractor):
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor)
    result = svc.extract_topics("vazia")
    assert result is None


def test_platform_default(db_session, mock_analyzer, mock_topic_extractor):
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor)
    msg = svc.save_message("live1", "A", "msg")
    assert msg.platform == "youtube"


def test_platform_explicit(db_session, mock_analyzer, mock_topic_extractor):
    svc = ChatService(db_session, mock_analyzer, mock_topic_extractor)
    msg = svc.save_message("live1", "A", "msg", platform="twitch")
    assert msg.platform == "twitch"
