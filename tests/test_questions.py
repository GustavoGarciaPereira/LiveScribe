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
    texts = ["Bom dia pessoal!", "Muito bom!", "Parabéns!"]
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


def test_questions_group_accent_variations():
    """Variacoes com e sem acento devem agrupar."""
    texts = [
        "Cadê o link da live?",
        "cade o link da live",
        "Que horas começa a live?",
    ]
    result = detect_questions(texts, min_length=10)
    cade_groups = [g for g in result if "cade" in g["text"].lower() or "cadê" in g["text"].lower()]
    assert len(cade_groups) >= 1
    assert cade_groups[0]["count"] >= 2


def test_questions_group_punctuation_variations():
    """Variacoes com pontuacao diferente devem agrupar."""
    texts = [
        "Que horas começa a live hoje?",
        "Que horas comeca a live hoje!",
        "Que horas começa a live hoje",
        "Vocês vão fazer live amanhã?",
    ]
    result = detect_questions(texts, min_length=10)
    horas_groups = [g for g in result if "horas" in g["text"].lower()]
    assert len(horas_groups) >= 1
    assert horas_groups[0]["count"] >= 3


def test_questions_dissimilar_stay_separate():
    """Perguntas diferentes nao devem agrupar."""
    texts = [
        "Cadê o link da live?",
        "Vocês vão fazer live amanhã?",
    ]
    result = detect_questions(texts, min_length=10)
    # Cada uma deve ser seu proprio grupo
    assert len(result) == 2
    for g in result:
        assert g["count"] == 1
