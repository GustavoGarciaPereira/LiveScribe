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


def test_sentiment_timeline_significance_first_bucket(db_session, mock_analyzer):
    """Primeiro bucket tem significant_change=False e change_direction='none'."""
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.analyze.return_value = {"Positivo": 3, "Negativo": 0, "Neutro": 0}
    mock.analyze_with_compound.return_value = ({"Positivo": 3, "Negativo": 0, "Neutro": 0}, [0.5, 0.6, 0.7])

    from datetime import datetime, timezone, timedelta
    from app.models.message import Message

    svc = ChatService(db_session, mock)
    base = datetime.now(timezone.utc)
    for i in range(3):
        db_session.add(Message(live_id="live-sig", author="A", message="Bom demais", created_at=base + timedelta(seconds=i)))
    db_session.commit()

    result = svc.sentiment_timeline("live-sig", interval_minutes=5)
    assert result is not None
    first = result["timeline"][0]
    assert first["significant_change"] is False
    assert first["p_value"] is None
    assert first["change_direction"] == "none"
    assert first["change_magnitude"] is None


def test_sentiment_timeline_significance_rise(db_session, mock_analyzer):
    """Dois buckets com medias diferentes devem detectar mudanca significativa."""
    from unittest.mock import MagicMock

    # Mock que retorna compounds diferentes para cada chamada
    mock = MagicMock()
    mock.analyze.return_value = {"Positivo": 3, "Negativo": 0, "Neutro": 0}

    call_count = [0]
    def analyze_with_compound_side_effect(texts):
        call_count[0] += 1
        if call_count[0] == 1:
            return {"Positivo": 3, "Negativo": 0, "Neutro": 0}, [-0.5, -0.4, -0.6]
        return {"Positivo": 3, "Negativo": 0, "Neutro": 0}, [0.8, 0.7, 0.9]

    mock.analyze_with_compound.side_effect = analyze_with_compound_side_effect

    from datetime import datetime, timezone, timedelta
    from app.models.message import Message

    svc = ChatService(db_session, mock)
    base = datetime.now(timezone.utc)
    # Bucket 1: mensagens negativas (primeiros 30 segundos)
    for i in range(3):
        db_session.add(Message(live_id="live-rise", author="A", message="Muito ruim", created_at=base + timedelta(seconds=i)))
    # Bucket 2: mensagens positivas (5+ minutos depois)
    for i in range(3):
        db_session.add(Message(live_id="live-rise", author="A", message="Muito bom", created_at=base + timedelta(seconds=300 + i)))
    db_session.commit()

    result = svc.sentiment_timeline("live-rise", interval_minutes=5)
    assert result is not None
    assert len(result["timeline"]) >= 2
    second = result["timeline"][1]
    assert second["significant_change"] is True, f"Esperado True, obtido {second}"
    assert second["p_value"] is not None and second["p_value"] < 0.05
    assert second["change_direction"] == "rise"


def test_sentiment_timeline_significance_stable(db_session, mock_analyzer):
    """Dois buckets com medias similares devem ser 'stable'."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.analyze.return_value = {"Positivo": 3, "Negativo": 0, "Neutro": 0}
    mock.analyze_with_compound.return_value = ({"Positivo": 3, "Negativo": 0, "Neutro": 0}, [0.1, 0.12, 0.11])

    from datetime import datetime, timezone, timedelta
    from app.models.message import Message

    svc = ChatService(db_session, mock)
    base = datetime.now(timezone.utc)
    for i in range(3):
        db_session.add(Message(live_id="live-stable", author="A", message="Tanto faz", created_at=base + timedelta(seconds=i)))
    for i in range(3):
        db_session.add(Message(live_id="live-stable", author="A", message="Tanto faz 2", created_at=base + timedelta(seconds=300 + i)))
    db_session.commit()

    result = svc.sentiment_timeline("live-stable", interval_minutes=5)
    assert result is not None
    assert len(result["timeline"]) >= 2
    second = result["timeline"][1]
    assert second["significant_change"] is False
    assert second["change_direction"] == "stable"


def test_sentiment_timeline_skip_empty_filters_buckets(db_session, mock_analyzer):
    """skip_empty=True remove buckets sem mensagens."""
    from datetime import datetime, timezone, timedelta
    from app.models.message import Message

    svc = ChatService(db_session, mock_analyzer)
    base = datetime.now(timezone.utc)
    # Duas mensagens com intervalo grande (simula duas sessoes)
    db_session.add(Message(live_id="live-skip", author="A", message="Msg 1", created_at=base))
    db_session.add(Message(live_id="live-skip", author="A", message="Msg 2", created_at=base + timedelta(hours=2)))
    db_session.commit()

    # Com skip_empty=True (padrao), buckets vazios sao removidos
    result = svc.sentiment_timeline("live-skip", interval_minutes=30)
    assert result is not None
    for b in result["timeline"]:
        assert b["total_messages"] > 0, f"Bucket vazio nao deveria estar na lista: {b}"

    # Com skip_empty=False, buckets vazios aparecem
    result_all = svc.sentiment_timeline("live-skip", interval_minutes=30, skip_empty=False)
    assert result_all is not None
    total = len(result_all["timeline"])
    non_empty = len(result["timeline"])
    assert total > non_empty, f"Esperado mais buckets com skip_empty=False ({total} > {non_empty})"


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


def test_user_isolation(db_session, mock_analyzer):
    """Usuarios diferentes veem apenas suas proprias mensagens."""
    svc = ChatService(db_session, mock_analyzer)
    # Usuario 1 salva 2 mensagens
    svc.save_message("live-iso", "A", "msg user1", user_id=1)
    svc.save_message("live-iso", "B", "outra msg user1", user_id=1)
    # Usuario 2 salva 1 mensagem
    svc.save_message("live-iso", "C", "msg user2", user_id=2)

    # User 1 ve 2 mensagens via list_lives
    lives_1 = svc.list_lives(user_id=1)
    assert len(lives_1) == 1
    assert lives_1[0]["total_messages"] == 2

    # User 2 ve 1 mensagem
    lives_2 = svc.list_lives(user_id=2)
    assert len(lives_2) == 1
    assert lives_2[0]["total_messages"] == 1

    # Sem user_id (= None) nao filtra — mostra todas
    lives_none = svc.list_lives(user_id=None)
    assert len(lives_none) == 1
    assert lives_none[0]["total_messages"] == 3  # todas as mensagens
