"""Testes para app/services/sarcasm.py e endpoint de sarcasmo."""

from app.services.sarcasm import LexiconSarcasmAnalyzer, SarcasmAnalyzer
from app.services.chat import ChatService


def test_analyzer_detects_sarcastic_phrase():
    analyzer = LexiconSarcasmAnalyzer()
    texts = ["aham, tá", "claro, confia", "sério mesmo?"]
    result = analyzer.analyze(texts)
    assert result["sarcastic"] == 3
    assert result["non_sarcastic"] == 0


def test_analyzer_normal_phrase_returns_zero():
    analyzer = LexiconSarcasmAnalyzer()
    texts = ["bom dia pessoal", "que live incrível", "obrigado pela atenção"]
    result = analyzer.analyze(texts)
    assert result["sarcastic"] == 0
    assert result["non_sarcastic"] == 3


def test_analyzer_sum_matches_total():
    analyzer = LexiconSarcasmAnalyzer()
    texts = [
        "aham, confia",           # sarcastic
        "bom dia",                # non_sarcastic
        "kkkk que novidade",      # sarcastic (kkkk + que novidade)
        "obrigado",               # non_sarcastic
    ]
    result = analyzer.analyze(texts)
    assert result["sarcastic"] + result["non_sarcastic"] == len(texts)


def test_analyzer_case_insensitive():
    analyzer = LexiconSarcasmAnalyzer()
    texts = ["AHAM, TÁ", "CLARO, CONFIA"]
    result = analyzer.analyze(texts)
    assert result["sarcastic"] == 2
    assert result["non_sarcastic"] == 0


def test_service_with_sarcasm_analyzer(db_session, mock_analyzer):
    from app.services.sarcasm import LexiconSarcasmAnalyzer

    sarcasm = LexiconSarcasmAnalyzer()
    svc = ChatService(db_session, mock_analyzer, sarcasm_analyzer=sarcasm)
    svc.save_message("live1", "A", "aham, tá")
    svc.save_message("live1", "B", "bom dia")
    svc.save_message("live1", "C", "claro, confia")

    result = svc.sarcasm_analysis("live1")
    assert result is not None
    assert result["live_id"] == "live1"
    assert result["total_messages"] == 3
    assert result["sarcasm"]["sarcastic"] == 2
    assert result["sarcasm"]["non_sarcastic"] == 1
    assert result["sarcasm"]["sarcastic"] + result["sarcasm"]["non_sarcastic"] == 3


def test_service_without_analyzer(db_session, mock_analyzer):
    svc = ChatService(db_session, mock_analyzer)
    svc.save_message("live1", "A", "aham, tá")

    result = svc.sarcasm_analysis("live1")
    assert result is not None
    assert result["sarcasm"]["sarcastic"] == 0
    assert result["sarcasm"]["non_sarcastic"] == 1
    assert result["total_messages"] == 1


def test_empty_live(db_session, mock_analyzer):
    svc = ChatService(db_session, mock_analyzer)
    result = svc.sarcasm_analysis("vazia")
    assert result is None


def test_route_sarcasm_with_data(auth_client):
    auth_client.post("/api/chat/messages", json={
        "live_id": "sarcasm-test",
        "author": "UserA",
        "message": "aham, confia",
    })
    auth_client.post("/api/chat/messages", json={
        "live_id": "sarcasm-test",
        "author": "UserB",
        "message": "bom dia",
    })

    response = auth_client.get("/api/chat/sarcasm-test/sarcasm")
    assert response.status_code == 200
    data = response.json()
    assert data["live_id"] == "sarcasm-test"
    assert data["total_messages"] == 2
    assert data["sarcasm"]["sarcastic"] >= 1
    assert data["sarcasm"]["non_sarcastic"] >= 1


def test_route_sarcasm_empty_live(auth_client):
    response = auth_client.get("/api/chat/empty-live/sarcasm")
    assert response.status_code == 404


def test_route_sarcasm_unauthenticated(client):
    response = client.get("/api/chat/some-live/sarcasm")
    assert response.status_code == 401
