"""Testes para app/services/questions.py."""

from app.services.questions import detect_questions


def test_detect_questions_with_questions():
    texts = [
        "Como faz para configurar o OBS?",
        "Que live incrível!",
        "alguém sabe como instalar o plugin?",
        "Eu gostei muito",
        "qual a diferença entre SSD e HDD?",
        "oi",
    ]
    result = detect_questions(texts, min_length=10)
    assert len(result) > 0
    total = sum(g["count"] for g in result)
    assert total >= 3


def test_detect_questions_empty():
    texts = ["Que live boa!", "Muito bom!", "Parabéns!"]
    result = detect_questions(texts, min_length=10)
    assert result == []


def test_detect_questions_min_length():
    texts = ["oi?", "como?", "e?"]
    result = detect_questions(texts, min_length=10)
    assert result == []


def test_detect_questions_groups_similar():
    texts = [
        "Como faz para instalar o plugin?",
        "como faço pra instalar o plugin",
        "alguém sabe como instalar o plugin?",
        "qual a diferença entre A e B?",
    ]
    result = detect_questions(texts, min_length=10)

    plugin_groups = [
        g for g in result
        if "plugin" in g["text"].lower()
        or any("plugin" in e.lower() for e in g["examples"])
    ]
    assert len(plugin_groups) > 0
    assert any(g["count"] >= 2 for g in plugin_groups)
