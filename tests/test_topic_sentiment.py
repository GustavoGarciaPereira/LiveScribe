"""Testes para o endpoint de sentimento por topico."""

from unittest.mock import MagicMock

from app.services.chat import ChatService


class TestTopicSentimentService:
    def test_with_data(self, db_session, mock_analyzer, mock_topic_extractor):
        """Topicos com sentimento definido — cruza topicos x sentimento."""
        # Mock emotion analyzer
        mock_emotion = MagicMock()
        mock_emotion.analyze.return_value = {"alegria": 3, "raiva": 0, "medo": 0, "surpresa": 0, "tristeza": 0, "nojo": 0}

        svc = ChatService(
            db_session, mock_analyzer, mock_topic_extractor,
            emotion_analyzer=mock_emotion,
        )

        # Adiciona mensagens com topicos claros
        svc.save_message("live1", "A", "Essa live esta incrivel demais")
        svc.save_message("live1", "B", "Live muito boa mesmo")
        svc.save_message("live1", "C", "Que live espetacular")

        result = svc.topic_sentiment("live1", top_n=5)
        assert result is not None
        assert result["live_id"] == "live1"
        assert len(result["topics"]) >= 1

        # O topico "live" (do mock) deve aparecer
        live_topic = next((t for t in result["topics"] if t["topic"] == "live"), None)
        assert live_topic is not None
        assert live_topic["message_count"] >= 1
        assert "Positivo" in live_topic["sentiment"]
        assert live_topic["dominant_emotion"] == "alegria"
        assert "statistics" in live_topic

    def test_no_messages_returns_none(self, db_session, mock_analyzer, mock_topic_extractor):
        """Live vazia retorna None."""
        svc = ChatService(db_session, mock_analyzer, mock_topic_extractor)
        result = svc.topic_sentiment("empty-live")
        assert result is None

    def test_emotion_dominant_correct(self, db_session, mock_analyzer):
        """Emocao dominante correta para mensagens de um topico."""
        from unittest.mock import MagicMock

        # Mock topic extractor que retorna um topico
        mock_topics = MagicMock()
        mock_topics.extract.return_value = [{"term": "raiva", "score": 0.9}]

        # Mock emotion que retorna raiva como dominante
        mock_emotion = MagicMock()
        mock_emotion.analyze.return_value = {"alegria": 0, "raiva": 5, "medo": 0, "surpresa": 0, "tristeza": 0, "nojo": 0}

        svc = ChatService(
            db_session, mock_analyzer, mock_topics,
            emotion_analyzer=mock_emotion,
        )

        svc.save_message("live1", "A", "Que raiva dessa situacao")
        svc.save_message("live1", "B", "Muita raiva mesmo")

        result = svc.topic_sentiment("live1", top_n=5)
        assert result is not None
        assert len(result["topics"]) == 1
        assert result["topics"][0]["dominant_emotion"] == "raiva"

    def test_sorting_by_message_count_descending(self, db_session, mock_analyzer):
        """Topicos ordenados por message_count decrescente."""
        from unittest.mock import MagicMock

        # Mock topic extractor com dois topicos
        mock_topics = MagicMock()
        mock_topics.extract.return_value = [
            {"term": "live", "score": 0.95},
            {"term": "incrivel", "score": 0.72},
        ]

        svc = ChatService(db_session, mock_analyzer, mock_topics)

        # "live" aparece em 2 mensagens, "incrivel" em 1
        svc.save_message("live1", "A", "Live muito boa")
        svc.save_message("live1", "B", "Essa live e top")
        svc.save_message("live1", "C", "Incrivel demais")

        result = svc.topic_sentiment("live1", top_n=5)
        assert result is not None
        assert len(result["topics"]) >= 1
        # Primeiro deve ser o com mais mensagens
        counts = [t["message_count"] for t in result["topics"]]
        assert counts == sorted(counts, reverse=True), f"Esperado decrescente, obtido {counts}"

    def test_transcript_snippet_varies_per_topic(self, db_session, mock_analyzer):
        """Topicos diferentes com picos em momentos diferentes tem snippets DIFERENTES."""
        from unittest.mock import MagicMock, patch

        mock_topics = MagicMock()
        mock_topics.extract.return_value = [
            {"term": "python", "score": 0.95},
            {"term": "encerrar", "score": 0.72},
        ]

        mock_emotion = MagicMock()
        mock_emotion.analyze.return_value = {"alegria": 1, "raiva": 0, "medo": 0, "surpresa": 0, "tristeza": 0, "nojo": 0}

        svc = ChatService(
            db_session, mock_analyzer, mock_topics,
            emotion_analyzer=mock_emotion,
        )

        from app.models.message import Message
        from datetime import datetime, timezone, timedelta

        base = datetime.now(timezone.utc)
        # Mensagens sobre "python" no inicio
        msgs = [
            Message(live_id="live-multi", author="A", message="Python legal", created_at=base),
            Message(live_id="live-multi", author="B", message="Python demais", created_at=base + timedelta(seconds=5)),
            Message(live_id="live-multi", author="C", message="Python show", created_at=base + timedelta(seconds=10)),
            # Mensagens sobre "encerrar" no final (2 min depois)
            Message(live_id="live-multi", author="D", message="Vou encerrar a live", created_at=base + timedelta(seconds=120)),
            Message(live_id="live-multi", author="E", message="Hora de encerrar", created_at=base + timedelta(seconds=125)),
        ]
        for m in msgs:
            db_session.add(m)
        db_session.commit()

        from app.services.transcript import TranscriptService
        # Transcript com trecho inicial e final
        FAKE_TRANSCRIPT_MULTI = [
            {"text": "Introducao sobre Python", "start": 0.0, "duration": 10.0},
            {"text": "codigo Python aqui", "start": 10.0, "duration": 5.0},
            {"text": "encerrando a live agora", "start": 130.0, "duration": 5.0},
            {"text": "ate a proxima", "start": 135.0, "duration": 5.0},
        ]

        TranscriptService.get_transcript.cache_clear()
        with patch.object(TranscriptService, "get_transcript", return_value=FAKE_TRANSCRIPT_MULTI):
            result = svc.topic_sentiment("live-multi", top_n=5, video_id="test-video-multi")

        assert result is not None
        assert len(result["topics"]) >= 2

        # Encontra cada topico
        py_topic = next(t for t in result["topics"] if t["topic"] == "python")
        end_topic = next(t for t in result["topics"] if t["topic"] == "encerrar")

        # Ambos devem ter transcript_snippet e devem ser diferentes
        assert py_topic["transcript_snippet"] is not None, "Topico python sem snippet"
        assert end_topic["transcript_snippet"] is not None, "Topico encerrar sem snippet"
        assert py_topic["transcript_snippet"] != end_topic["transcript_snippet"], (
            f"Snippets iguais: ambos '{py_topic['transcript_snippet']}'"
        )
        # O snippet do python deve mencionar Python (trecho inicial)
        assert "Python" in py_topic["transcript_snippet"] or "python" in py_topic["transcript_snippet"]
        # O snippet do encerrar deve mencionar encerramento (trecho final)
        assert "encerrando" in end_topic["transcript_snippet"] or "proxima" in end_topic["transcript_snippet"]


class TestTopicSentimentRoute:
    def test_returns_200_with_data(self, auth_client):
        """Endpoint retorna 200 com dados validos."""
        auth_client.post("/api/chat/messages", json={
            "live_id": "live-ts-1",
            "author": "User",
            "message": "Live incrivel demais!",
            "platform": "youtube",
        })
        resp = auth_client.get("/api/chat/live-ts-1/topic-sentiment?top_n=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["live_id"] == "live-ts-1"
        assert "topics" in data

    def test_404_when_no_messages(self, auth_client):
        """Endpoint retorna 404 para live sem mensagens."""
        resp = auth_client.get("/api/chat/nonexistent-live-ts/topic-sentiment")
        assert resp.status_code == 404

    def test_requires_auth(self, client):
        """Endpoint requer autenticacao."""
        resp = client.get("/api/chat/some-live/topic-sentiment")
        assert resp.status_code in (401, 403)
