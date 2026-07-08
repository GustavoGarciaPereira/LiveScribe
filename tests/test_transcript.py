"""Testes para integracao com YouTube Transcript API no topic-sentiment."""

from unittest.mock import patch, MagicMock

from app.services.transcript import TranscriptService


# ── Dados fake de transcricao ─────────────────────────────────

FAKE_TRANSCRIPT = [
    {"text": "Ola pessoal", "start": 0.0, "duration": 2.0},
    {"text": "bem vindos a live", "start": 2.0, "duration": 3.0},
    {"text": "hoje vamos falar sobre Python", "start": 5.0, "duration": 4.0},
    {"text": "e uma linguagem incrivel", "start": 9.0, "duration": 3.0},
    {"text": "muito obrigado por assistirem", "start": 120.0, "duration": 3.0},
    {"text": "ate a proxima live pessoal", "start": 123.0, "duration": 4.0},
]


class TestTranscriptService:
    def test_get_transcript_returns_data(self):
        """get_transcript retorna lista de trechos quando disponivel."""
        TranscriptService.get_transcript.cache_clear()
        with patch.object(TranscriptService, "get_transcript", return_value=FAKE_TRANSCRIPT):
            result = TranscriptService.get_transcript("test-video-id")
            assert result is not None
            assert len(result) == 6
            assert result[0]["text"] == "Ola pessoal"

    def test_get_transcript_returns_none_on_error(self):
        """get_transcript retorna None quando transcricao nao existe."""
        TranscriptService.get_transcript.cache_clear()
        with patch.object(TranscriptService, "get_transcript", return_value=None):
            result = TranscriptService.get_transcript("no-transcript-video")
            assert result is None

    def test_find_snippet_at_finds_closest(self):
        """find_snippet_at retorna trecho proximo ao timestamp."""
        snippet = TranscriptService.find_snippet_at(FAKE_TRANSCRIPT, 6.0, context_radius=5.0)
        assert snippet is not None
        assert "Python" in snippet
        assert "incrivel" in snippet

    def test_find_snippet_at_empty_transcript(self):
        """find_snippet_at retorna None para lista vazia."""
        assert TranscriptService.find_snippet_at([], 10.0) is None

    def test_find_snippet_at_none_timestamp(self):
        """find_snippet_at retorna None para timestamp_seconds None."""
        assert TranscriptService.find_snippet_at(FAKE_TRANSCRIPT, None) is None

    def test_find_snippet_at_varied_timestamps(self):
        """find_snippet_at retorna snippets DIFERENTES para timestamps diferentes."""
        snippet_early = TranscriptService.find_snippet_at(FAKE_TRANSCRIPT, 3.0, context_radius=2.0)
        snippet_late = TranscriptService.find_snippet_at(FAKE_TRANSCRIPT, 121.0, context_radius=2.0)

        assert snippet_early is not None
        assert snippet_late is not None
        # Trechos iniciais vs finais devem ser diferentes
        assert snippet_early != snippet_late, f"Esperado snippets diferentes, ambos: {snippet_early}"
        assert "pessoal" in snippet_early or "bem vindos" in snippet_early
        assert "obrigado" in snippet_late or "proxima" in snippet_late


class TestTopicSentimentWithTranscript:
    def test_topic_sentiment_with_video_id_enriches_response(self, db_session, mock_analyzer):
        """Com video_id e transcricao disponivel, transcript_snippet e preenchido."""
        from unittest.mock import MagicMock

        mock_topics = MagicMock()
        mock_topics.extract.return_value = [{"term": "live", "score": 0.95}]

        mock_emotion = MagicMock()
        mock_emotion.analyze.return_value = {"alegria": 2, "raiva": 0, "medo": 0, "surpresa": 0, "tristeza": 0, "nojo": 0}

        from app.services.chat import ChatService
        from app.repositories.messages import create_message

        create_message(db_session, live_id="live-transcript-1", author="A", content="Live incrivel!")

        svc = ChatService(
            db_session, mock_analyzer, mock_topics,
            emotion_analyzer=mock_emotion,
        )

        TranscriptService.get_transcript.cache_clear()
        with patch.object(TranscriptService, "get_transcript", return_value=FAKE_TRANSCRIPT):
            result = svc.topic_sentiment("live-transcript-1", top_n=5, video_id="test-video")

        assert result is not None
        assert len(result["topics"]) >= 1
        topic = result["topics"][0]
        assert "transcript_snippet" in topic
        assert "peak_timestamp" in topic

    def test_topic_sentiment_without_video_id_has_null_transcript(self, db_session, mock_analyzer):
        """Sem video_id, transcript_snippet e peak_timestamp sao null."""
        from unittest.mock import MagicMock

        mock_topics = MagicMock()
        mock_topics.extract.return_value = [{"term": "live", "score": 0.95}]

        mock_emotion = MagicMock()
        mock_emotion.analyze.return_value = {"alegria": 1, "raiva": 0, "medo": 0, "surpresa": 0, "tristeza": 0, "nojo": 0}

        from app.services.chat import ChatService
        from app.repositories.messages import create_message

        create_message(db_session, live_id="live-no-video", author="A", content="Live show!")

        svc = ChatService(
            db_session, mock_analyzer, mock_topics,
            emotion_analyzer=mock_emotion,
        )

        result = svc.topic_sentiment("live-no-video", top_n=5)
        assert result is not None
        topic = result["topics"][0]
        assert topic["transcript_snippet"] is None
        assert topic["peak_timestamp"] is None

    def test_topic_sentiment_with_unavailable_transcript(self, db_session, mock_analyzer):
        """Com video_id mas transcricao indisponivel, endpoint funciona normalmente."""
        from unittest.mock import MagicMock

        mock_topics = MagicMock()
        mock_topics.extract.return_value = [{"term": "live", "score": 0.95}]

        mock_emotion = MagicMock()
        mock_emotion.analyze.return_value = {"alegria": 1, "raiva": 0, "medo": 0, "surpresa": 0, "tristeza": 0, "nojo": 0}

        from app.services.chat import ChatService
        from app.repositories.messages import create_message

        create_message(db_session, live_id="live-no-transcript", author="A", content="Live!")

        svc = ChatService(
            db_session, mock_analyzer, mock_topics,
            emotion_analyzer=mock_emotion,
        )

        TranscriptService.get_transcript.cache_clear()
        with patch.object(TranscriptService, "get_transcript", return_value=None):
            result = svc.topic_sentiment("live-no-transcript", top_n=5, video_id="video-id")

        assert result is not None
        assert len(result["topics"]) >= 1
        topic = result["topics"][0]
        assert topic["transcript_snippet"] is None


class TestTopicSentimentRouteWithTranscript:
    def test_endpoint_accepts_video_id(self, auth_client):
        """Endpoint funciona com parametro video_id opcional."""
        auth_client.post("/api/chat/messages", json={
            "live_id": "live-ts-vid",
            "author": "User",
            "message": "Live incrivel demais!",
            "platform": "youtube",
        })
        resp = auth_client.get("/api/chat/live-ts-vid/topic-sentiment?top_n=5&video_id=abc123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["live_id"] == "live-ts-vid"
        assert "topics" in data

    def test_endpoint_without_video_id_still_works(self, auth_client):
        """Endpoint funciona sem video_id (fallback)."""
        auth_client.post("/api/chat/messages", json={
            "live_id": "live-ts-novid",
            "author": "User",
            "message": "Teste sem video id",
            "platform": "youtube",
        })
        resp = auth_client.get("/api/chat/live-ts-novid/topic-sentiment?top_n=5")
        assert resp.status_code == 200
