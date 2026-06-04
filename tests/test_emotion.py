"""Testes para app/services/emotion.py e endpoint de emoções."""

from app.services.emotion import LexiconEmotionAnalyzer
from app.services.chat import ChatService


def test_analyzer_detects_alegria():
    analyzer = LexiconEmotionAnalyzer()
    texts = ["Que live maravilhosa! Estou muito feliz e animado!"]
    result = analyzer.analyze(texts)
    assert result["alegria"] == 1


def test_analyzer_detects_raiva():
    analyzer = LexiconEmotionAnalyzer()
    texts = ["Isso é um absurdo! Que raiva dessa palhaçada!"]
    result = analyzer.analyze(texts)
    assert result["raiva"] == 1


def test_analyzer_detects_tristeza():
    analyzer = LexiconEmotionAnalyzer()
    texts = ["Que triste, estou chorando aqui. Muita saudade."]
    result = analyzer.analyze(texts)
    assert result["tristeza"] == 1


def test_analyzer_detects_surpresa():
    analyzer = LexiconEmotionAnalyzer()
    texts = ["Nossa! Que surpresa impressionante! Chocado!"]
    result = analyzer.analyze(texts)
    assert result["surpresa"] == 1


def test_analyzer_detects_medo():
    analyzer = LexiconEmotionAnalyzer()
    texts = ["Que medo! Isso é assustador, estou apavorado!"]
    result = analyzer.analyze(texts)
    assert result["medo"] == 1


def test_analyzer_detects_nojo():
    analyzer = LexiconEmotionAnalyzer()
    texts = ["Que nojo! Isso é repugnante e nojento!"]
    result = analyzer.analyze(texts)
    assert result["nojo"] == 1


def test_analyzer_neutral_balanced():
    analyzer = LexiconEmotionAnalyzer()
    texts = ["A live começa às 20h."]
    result = analyzer.analyze(texts)
    assert all(v == 0 for v in result.values())


def test_emotion_timeline_buckets_correctly(db_session, mock_analyzer):
    from app.services.emotion import EmotionAnalyzer

    class FakeEmotionAnalyzer(EmotionAnalyzer):
        def analyze(self, texts):
            return {"alegria": 2, "raiva": 1, "medo": 0, "surpresa": 0, "tristeza": 0, "nojo": 0}

    emotion = FakeEmotionAnalyzer()
    svc = ChatService(db_session, mock_analyzer, emotion_analyzer=emotion)
    svc.save_message("live1", "A", "msg1")
    svc.save_message("live1", "B", "msg2")
    svc.save_message("live1", "C", "msg3")

    result = svc.emotion_timeline("live1", interval_minutes=1)
    assert result is not None
    assert result["live_id"] == "live1"
    assert len(result["timeline"]) >= 1
    bucket = result["timeline"][0]
    assert bucket["total_messages"] == 3
    assert bucket["alegria"] == 2
    assert bucket["raiva"] == 1


def test_emotion_timeline_empty_live(db_session, mock_analyzer):
    svc = ChatService(db_session, mock_analyzer)
    result = svc.emotion_timeline("vazia")
    assert result is None
