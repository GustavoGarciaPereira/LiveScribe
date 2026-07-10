"""Testes para app/services/aspects.py e endpoint de aspecto-sentiment."""

from app.services.aspects import LexiconAspectAnalyzer, AspectAnalyzer
from app.services.chat import ChatService
from app.services.sentiment import LeiaSentimentAnalyzer


def test_analyzer_detects_known_entity():
    analyzer = LexiconAspectAnalyzer()
    texts = ["O bruno é incrível!", "O breno mandou bem demais!"]
    result = analyzer.analyze(texts)
    assert "bruno" in result
    assert result["bruno"]["messages"] == 1
    assert "breno" in result
    assert result["breno"]["messages"] == 1
    assert sum(result["bruno"]["sentiment"].values()) == 1


def test_analyzer_no_mentions_returns_empty():
    analyzer = LexiconAspectAnalyzer()
    texts = ["bom dia", "que legal", "obrigado"]
    result = analyzer.analyze(texts)
    # Todas as entidades devem ter messages=0
    for entity, data in result.items():
        assert data["messages"] == 0


def test_analyzer_custom_entities():
    analyzer = LexiconAspectAnalyzer()
    texts = ["O lula é fera!", "O bolsonaro também é brabo!"]
    result = analyzer.analyze(texts, entities=["lula"])
    assert "lula" in result
    assert result["lula"]["messages"] == 1
    assert "bolsonaro" not in result  # filtrado


def test_analyzer_sentiment_calculated():
    """Verifica que o sentimento e calculado corretamente."""
    analyzer = LexiconAspectAnalyzer(sentiment_analyzer=LeiaSentimentAnalyzer())
    texts = [
        "bruno é horrível, muito ruim",  # Negativo
        "bruno é incrível, parabéns!",    # Positivo
        "bom dia bruno",                  # Neutro
    ]
    result = analyzer.analyze(texts, entities=["bruno"])
    assert result["bruno"]["messages"] == 3
    total = sum(result["bruno"]["sentiment"].values())
    assert total == 3


def test_service_with_aspect_analyzer(db_session, mock_analyzer):
    from app.services.aspects import LexiconAspectAnalyzer

    aspect = LexiconAspectAnalyzer()
    svc = ChatService(db_session, mock_analyzer, aspect_analyzer=aspect)
    svc.save_message("live1", "A", "O bruno mandou bem")
    svc.save_message("live1", "B", "O breno é show")

    result = svc.aspect_sentiment("live1")
    assert result is not None
    assert result["live_id"] == "live1"
    assert "bruno" in result["aspects"]
    assert "breno" in result["aspects"]
    assert result["aspects"]["bruno"]["messages"] == 1
    assert result["aspects"]["breno"]["messages"] == 1


def test_service_without_analyzer(db_session, mock_analyzer):
    svc = ChatService(db_session, mock_analyzer)
    svc.save_message("live1", "A", "O bruno mandou bem")

    result = svc.aspect_sentiment("live1")
    assert result is not None
    assert result["aspects"] == {}


def test_empty_live(db_session, mock_analyzer):
    svc = ChatService(db_session, mock_analyzer)
    result = svc.aspect_sentiment("vazia")
    assert result is None


def test_route_aspect_sentiment_with_data(auth_client):
    auth_client.post("/api/chat/messages", json={
        "live_id": "aspect-test",
        "author": "A",
        "message": "O bruno mandou bem demais!",
    })
    response = auth_client.get("/api/chat/aspect-test/aspect-sentiment")
    assert response.status_code == 200
    data = response.json()
    assert data["live_id"] == "aspect-test"
    assert "bruno" in data["aspects"]
    assert data["aspects"]["bruno"]["messages"] >= 1


def test_route_aspect_sentiment_with_entities_filter(auth_client):
    auth_client.post("/api/chat/messages", json={
        "live_id": "aspect-filter",
        "author": "A",
        "message": "bruno e breno são top",
    })
    # Filtra apenas breno
    response = auth_client.get("/api/chat/aspect-filter/aspect-sentiment?entities=breno")
    assert response.status_code == 200
    data = response.json()
    assert "breno" in data["aspects"]
    assert data["aspects"]["breno"]["messages"] >= 1
    # bruno não deve aparecer se usamos entities filter
    for key in data["aspects"]:
        if key != "breno":
            assert data["aspects"][key]["messages"] == 0


def test_route_aspect_sentiment_empty_live(auth_client):
    response = auth_client.get("/api/chat/empty-live/aspect-sentiment")
    assert response.status_code == 404


def test_route_aspect_sentiment_unauthenticated(client):
    response = client.get("/api/chat/some-live/aspect-sentiment")
    assert response.status_code == 401
