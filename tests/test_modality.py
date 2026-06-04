"""Testes para app/services/modality.py e endpoint de modalização."""

from app.services.modality import LexiconModalityAnalyzer
from app.services.chat import ChatService


def test_analyzer_detects_certeza():
    analyzer = LexiconModalityAnalyzer()
    texts = [
        "Com certeza isso vai funcionar! É fato.",
        "Isso é óbvio e evidente para todos.",
    ]
    result = analyzer.analyze(texts)
    assert result["certeza"] > 0


def test_analyzer_detects_duvida():
    analyzer = LexiconModalityAnalyzer()
    texts = [
        "Talvez isso funcione, mas não sei.",
        "Será que é verdade? Acho que não.",
    ]
    result = analyzer.analyze(texts)
    assert result["duvida"] > 0


def test_analyzer_detects_enfase():
    analyzer = LexiconModalityAnalyzer()
    texts = [
        "Isso é muito incrível e super fantástico!",
        "Realmente maravilhoso demais.",
    ]
    result = analyzer.analyze(texts)
    assert result["enfase"] > 0


def test_modality_timeline_buckets_correctly(db_session, mock_analyzer):
    from app.services.modality import ModalityAnalyzer

    class FakeModalityAnalyzer(ModalityAnalyzer):
        def analyze(self, texts):
            return {"certeza": 2, "duvida": 1, "enfase": 3}

    modality = FakeModalityAnalyzer()
    svc = ChatService(db_session, mock_analyzer, modality_analyzer=modality)
    svc.save_message("live1", "A", "msg1")
    svc.save_message("live1", "B", "msg2")
    svc.save_message("live1", "C", "msg3")

    result = svc.modality_timeline("live1", interval_minutes=5)
    assert result is not None
    assert result["live_id"] == "live1"
    assert len(result["timeline"]) >= 1
    bucket = result["timeline"][0]
    assert bucket["total_messages"] == 3
    assert bucket["certeza"] == 2
    assert bucket["duvida"] == 1
    assert bucket["enfase"] == 3


def test_modality_timeline_empty_live(db_session, mock_analyzer):
    svc = ChatService(db_session, mock_analyzer)
    result = svc.modality_timeline("vazia")
    assert result is None
