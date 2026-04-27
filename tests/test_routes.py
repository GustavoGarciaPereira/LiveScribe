"""Testes de integração para as rotas da API."""


class TestHealthcheck:
    def test_healthcheck(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "online"}


class TestPostMessage:
    def test_valid(self, client):
        response = client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "User", "message": "Teste"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert data["author"] == "User"
        assert data["message"] == "Teste"
        assert data["id"] is not None

    def test_missing_fields(self, client):
        response = client.post(
            "/api/chat/messages",
            json={"author": "User"},
        )
        assert response.status_code == 422  # validation error

    def test_empty_body(self, client):
        response = client.post("/api/chat/messages", json={})
        assert response.status_code == 422


class TestWordFrequency:
    def test_valid(self, client):
        # Insere duas mensagens
        client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "gato gato cachorro"},
        )
        client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "B", "message": "gato passarinho"},
        )

        response = client.get("/api/chat/live1/word-frequency?top_n=10")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert data["word_frequency"][0]["palavra"] == "gato"
        assert data["word_frequency"][0]["frequencia"] == 3

    def test_404_when_no_messages(self, client):
        response = client.get("/api/chat/naoexiste/word-frequency")
        assert response.status_code == 404


class TestSentiment:
    def test_valid(self, client):
        client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Que live incrível!"},
        )

        response = client.get("/api/chat/live1/sentiment")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert data["total_messages_analyzed"] == 1
        assert "sentiment_summary" in data
        # O mock sempre retorna Neutro
        assert data["sentiment_summary"]["Neutro"] == 1

    def test_404_when_no_messages(self, client):
        response = client.get("/api/chat/vazia/sentiment")
        assert response.status_code == 404

    def test_internal_server_error(self, client, mock_analyzer):
        """Simula erro 500 forçando falha no analisador de sentimento."""
        mock_analyzer.analyze.side_effect = RuntimeError("Falha simulada")
        client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Teste"},
        )
        response = client.get("/api/chat/live1/sentiment")
        assert response.status_code == 500
        assert "detail" in response.json()


class TestPlatform:
    def test_default_platform(self, client):
        response = client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Teste"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "youtube"

    def test_explicit_platform(self, client):
        response = client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Teste", "platform": "twitch"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "twitch"


class TestListLives:
    def test_with_data(self, client):
        client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "M1"},
        )
        client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "B", "message": "M2"},
        )
        client.post(
            "/api/chat/messages",
            json={"live_id": "live2", "author": "C", "message": "M3"},
        )

        response = client.get("/api/chat/lives")
        assert response.status_code == 200
        data = response.json()
        assert data["total_lives"] == 2
        lives = data["lives"]
        assert lives[0]["live_id"] == "live2"  # mais recente primeiro
        assert lives[0]["total_messages"] == 1

    def test_empty(self, client):
        response = client.get("/api/chat/lives")
        assert response.status_code == 200
        data = response.json()
        assert data["total_lives"] == 0
        assert data["lives"] == []


class TestSentimentTimeline:
    def test_with_data(self, client):
        client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Que incrível!"},
        )
        response = client.get("/api/chat/live1/sentiment-timeline?interval_minutes=5")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert data["interval_minutes"] == 5
        assert len(data["timeline"]) >= 1
        assert "sentiments" in data["timeline"][0]

    def test_empty(self, client):
        response = client.get("/api/chat/vazia/sentiment-timeline")
        assert response.status_code == 404

    def test_custom_interval(self, client):
        client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Teste"},
        )
        response = client.get("/api/chat/live1/sentiment-timeline?interval_minutes=10")
        assert response.status_code == 200
        data = response.json()
        assert data["interval_minutes"] == 10


class TestEngagementPeaks:
    def test_with_data(self, client):
        client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Teste"},
        )
        response = client.get("/api/chat/live1/engagement-peaks?top_n=3")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert isinstance(data["peaks"], list)

    def test_empty(self, client):
        response = client.get("/api/chat/vazia/engagement-peaks")
        assert response.status_code == 404


class TestTopics:
    def test_with_data(self, client):
        client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "live incrível"},
        )
        response = client.get("/api/chat/live1/topics?top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert isinstance(data["topics"], list)

    def test_empty(self, client):
        response = client.get("/api/chat/vazia/topics")
        assert response.status_code == 404
