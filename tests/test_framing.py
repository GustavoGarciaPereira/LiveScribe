"""Testes para app/services/framing.py e endpoint de enquadramento (framing)."""

from app.services.framing import LexiconFramingAnalyzer, FramingAnalyzer
from app.services.chat import ChatService


def test_analyzer_detects_ataque():
    analyzer = LexiconFramingAnalyzer()
    texts = ["seu idiota", "você é burro e ridículo"]
    result = analyzer.analyze(texts)
    assert result["ataque"] > 0
    assert result["neutro"] == 0


def test_analyzer_detects_elogio():
    analyzer = LexiconFramingAnalyzer()
    texts = ["parabéns, excelente trabalho!", "você é incrível e fantástico"]
    result = analyzer.analyze(texts)
    assert result["elogio"] > 0
    assert result["neutro"] == 0


def test_analyzer_detects_ironia():
    analyzer = LexiconFramingAnalyzer()
    texts = ["kkkk sério?", "aham, tá"]
    result = analyzer.analyze(texts)
    assert result["ironia"] > 0
    assert result["neutro"] == 0


def test_analyzer_detects_defesa():
    analyzer = LexiconFramingAnalyzer()
    texts = ["concordo plenamente", "exatamente, falou tudo"]
    result = analyzer.analyze(texts)
    assert result["defesa"] > 0
    assert result["neutro"] == 0


def test_analyzer_detects_pergunta():
    analyzer = LexiconFramingAnalyzer()
    texts = ["quem vai participar?", "alguém sabe que horas começa?"]
    result = analyzer.analyze(texts)
    assert result["pergunta"] > 0
    assert result["neutro"] == 0


def test_analyzer_fallback_to_neutro():
    analyzer = LexiconFramingAnalyzer()
    texts = ["bom dia a todos", "não sei o que dizer"]
    result = analyzer.analyze(texts)
    assert result["neutro"] == 2
    total_non_neutro = sum(v for k, v in result.items() if k != "neutro")
    assert total_non_neutro == 0


def test_analyzer_sum_matches_total():
    """Verifica que a soma das contagens é igual ao total de mensagens."""
    analyzer = LexiconFramingAnalyzer()
    texts = [
        "seu idiota",           # ataque
        "parabéns, ótimo!",      # elogio
        "kkkk aham",             # ironia
        "concordo plenamente",   # defesa
        "quem vai?",             # pergunta
        "bom dia",               # neutro
    ]
    result = analyzer.analyze(texts)
    total = sum(result.values())
    assert total == len(texts)


def test_analyzer_multiple_categories_same_message():
    """Mensagem com palavras de múltiplas categorias conta em todas."""
    analyzer = LexiconFramingAnalyzer()
    texts = ["que piada, seu idiota concordo com isso?"]
    result = analyzer.analyze(texts)
    assert result["ataque"] >= 1
    assert result["ironia"] >= 1
    assert result["defesa"] >= 1
    assert result["neutro"] == 0


def test_analyzer_case_insensitive():
    analyzer = LexiconFramingAnalyzer()
    texts = ["IDIOTA", "PARABÉNS", "KKKK"]
    result = analyzer.analyze(texts)
    assert result["ataque"] == 1
    assert result["elogio"] == 1
    assert result["ironia"] == 1
    assert result["neutro"] == 0


def test_service_with_framing_analyzer(db_session, mock_analyzer):
    """Testa o método framing_analysis do ChatService com analyzer real."""
    from app.services.framing import LexiconFramingAnalyzer

    framing = LexiconFramingAnalyzer()
    svc = ChatService(db_session, mock_analyzer, framing_analyzer=framing)
    svc.save_message("live1", "A", "seu idiota")
    svc.save_message("live1", "B", "parabéns, excelente!")
    svc.save_message("live1", "C", "kkkk aham")

    result = svc.framing_analysis("live1")
    assert result is not None
    assert result["live_id"] == "live1"
    assert result["total_messages"] == 3
    assert result["framing"]["ataque"] >= 1
    assert result["framing"]["elogio"] >= 1
    assert result["framing"]["ironia"] >= 1
    assert result["framing"]["neutro"] == 0
    total = sum(result["framing"].values())
    assert total == 3


def test_service_without_analyzer(db_session, mock_analyzer):
    """ChatService sem framing_analyzer retorna contagens zeradas."""
    svc = ChatService(db_session, mock_analyzer)
    svc.save_message("live1", "A", "seu idiota")

    result = svc.framing_analysis("live1")
    assert result is not None
    assert result["framing"]["ataque"] == 0
    assert result["framing"]["neutro"] == 1
    assert result["total_messages"] == 1


def test_empty_live(db_session, mock_analyzer):
    """Live sem mensagens retorna None."""
    svc = ChatService(db_session, mock_analyzer)
    result = svc.framing_analysis("vazia")
    assert result is None


def test_route_framing_with_data(auth_client):
    """Testa o endpoint de framing com mensagens no banco."""
    # Adiciona algumas mensagens
    auth_client.post("/api/chat/messages", json={
        "live_id": "framing-test",
        "author": "UserA",
        "message": "seu idiota",
    })
    auth_client.post("/api/chat/messages", json={
        "live_id": "framing-test",
        "author": "UserB",
        "message": "parabéns, ótimo trabalho!",
    })
    auth_client.post("/api/chat/messages", json={
        "live_id": "framing-test",
        "author": "UserC",
        "message": "bom dia",
    })

    response = auth_client.get("/api/chat/framing-test/framing")
    assert response.status_code == 200
    data = response.json()
    assert data["live_id"] == "framing-test"
    assert data["total_messages"] == 3
    assert data["framing"]["ataque"] >= 1
    assert data["framing"]["elogio"] >= 1
    assert data["framing"]["neutro"] >= 1
    total = sum(data["framing"].values())
    assert total == 3


def test_route_framing_empty_live(auth_client):
    """Live vazia retorna 404."""
    response = auth_client.get("/api/chat/empty-live/framing")
    assert response.status_code == 404


def test_route_framing_unauthenticated(client):
    """Sem autenticação retorna 401."""
    response = client.get("/api/chat/some-live/framing")
    assert response.status_code == 401
