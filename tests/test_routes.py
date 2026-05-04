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
    def test_valid(self, client, auth_client):
        # Insere duas mensagens
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "gato gato cachorro"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "B", "message": "gato passarinho"},
        )

        response = auth_client.get("/api/chat/live1/word-frequency?top_n=10")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert data["word_frequency"][0]["palavra"] == "gato"
        assert data["word_frequency"][0]["frequencia"] == 3

    def test_404_when_no_messages(self, client, auth_client):
        response = auth_client.get("/api/chat/naoexiste/word-frequency")
        assert response.status_code == 404


class TestSentiment:
    def test_valid(self, client, auth_client):
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Que live incrível!"},
        )

        response = auth_client.get("/api/chat/live1/sentiment")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert data["total_messages_analyzed"] == 1
        assert "sentiment_summary" in data
        # O mock sempre retorna Neutro
        assert data["sentiment_summary"]["Neutro"] == 1

    def test_404_when_no_messages(self, client, auth_client):
        response = auth_client.get("/api/chat/vazia/sentiment")
        assert response.status_code == 404

    def test_internal_server_error(self, client, auth_client, mock_analyzer):
        """Simula erro 500 forçando falha no analisador de sentimento."""
        mock_analyzer.analyze.side_effect = RuntimeError("Falha simulada")
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Teste"},
        )
        response = auth_client.get("/api/chat/live1/sentiment")
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
    def test_with_data(self, client, auth_client):
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "M1"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "B", "message": "M2"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live2", "author": "C", "message": "M3"},
        )

        response = auth_client.get("/api/chat/lives")
        assert response.status_code == 200
        data = response.json()
        assert data["total_lives"] == 2
        lives = data["lives"]
        assert lives[0]["live_id"] == "live2"  # mais recente primeiro
        assert lives[0]["total_messages"] == 1

    def test_empty(self, client, auth_client):
        response = auth_client.get("/api/chat/lives")
        assert response.status_code == 200
        data = response.json()
        assert data["total_lives"] == 0
        assert data["lives"] == []


class TestSentimentTimeline:
    def test_with_data(self, client, auth_client):
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Que incrível!"},
        )
        response = auth_client.get("/api/chat/live1/sentiment-timeline?interval_minutes=5")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert data["interval_minutes"] == 5
        assert len(data["timeline"]) >= 1
        assert "sentiments" in data["timeline"][0]

    def test_empty(self, client, auth_client):
        response = auth_client.get("/api/chat/vazia/sentiment-timeline")
        assert response.status_code == 404

    def test_custom_interval(self, client, auth_client):
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Teste"},
        )
        response = auth_client.get("/api/chat/live1/sentiment-timeline?interval_minutes=10")
        assert response.status_code == 200
        data = response.json()
        assert data["interval_minutes"] == 10


class TestEngagementPeaks:
    def test_with_data(self, client, auth_client):
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "Teste"},
        )
        response = auth_client.get("/api/chat/live1/engagement-peaks?top_n=3")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert isinstance(data["peaks"], list)

    def test_empty(self, client, auth_client):
        response = auth_client.get("/api/chat/vazia/engagement-peaks")
        assert response.status_code == 404


class TestTopicTimeline:
    def test_term_present(self, client, auth_client):
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "gato bonito"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "B", "message": "cachorro legal"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "C", "message": "gato bravo"},
        )

        response = auth_client.get("/api/chat/live1/topic-timeline?term=gato&interval_minutes=5")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert data["term"] == "gato"
        assert data["interval_minutes"] == 5
        assert len(data["timeline"]) >= 1
        bucket = data["timeline"][0]
        assert bucket["count"] == 2  # "gato bonito" e "gato bravo"
        assert bucket["total_messages"] == 3

    def test_term_absent(self, client, auth_client):
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "cachorro legal"},
        )
        response = auth_client.get("/api/chat/live1/topic-timeline?term=gato&interval_minutes=5")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert data["term"] == "gato"
        assert all(bucket["count"] == 0 for bucket in data["timeline"])

    def test_nonexistent_live(self, client, auth_client):
        response = auth_client.get("/api/chat/naoexiste/topic-timeline?term=gato")
        assert response.status_code == 404


class TestTopics:
    def test_with_data(self, client, auth_client):
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "live incrível"},
        )
        response = auth_client.get("/api/chat/live1/topics?top_n=5")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert isinstance(data["topics"], list)

    def test_empty(self, client, auth_client):
        response = auth_client.get("/api/chat/vazia/topics")
        assert response.status_code == 404

class TestTopAuthors:
    def test_with_data(self, client, auth_client):
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "Fulano", "message": "Boa noite"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "Fulano", "message": "Mais uma"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "Ciclano", "message": "Soh uma"},
        )

        response = auth_client.get("/api/chat/live1/top-authors?top_n=10")
        assert response.status_code == 200
        data = response.json()
        assert data["live_id"] == "live1"
        assert data["total_authors"] == 2
        assert len(data["authors"]) == 2
        assert data["authors"][0]["author"] == "Fulano"
        assert data["authors"][0]["messages"] == 2
        assert data["authors"][1]["author"] == "Ciclano"
        assert data["authors"][1]["messages"] == 1

    def test_empty_live(self, client, auth_client):
        response = auth_client.get("/api/chat/vazia/top-authors")
        assert response.status_code == 404

    def test_sorting(self, client, auth_client):
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "C", "message": "uma"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "B", "message": "duas"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "B", "message": "duas"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "tres"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "tres"},
        )
        auth_client.post(
            "/api/chat/messages",
            json={"live_id": "live1", "author": "A", "message": "tres"},
        )

        response = auth_client.get("/api/chat/live1/top-authors?top_n=3")
        assert response.status_code == 200
        data = response.json()
        authors = data["authors"]
        assert authors[0]["author"] == "A"
        assert authors[0]["messages"] == 3
        assert authors[1]["author"] == "B"
        assert authors[1]["messages"] == 2
        assert authors[2]["author"] == "C"
        assert authors[2]["messages"] == 1

