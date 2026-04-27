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
