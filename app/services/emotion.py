from abc import ABC, abstractmethod

from app.core.emotion_lexicon import EMOTION_LEXICON

EMOTIONS = ["alegria", "raiva", "medo", "surpresa", "tristeza", "nojo"]


class EmotionAnalyzer(ABC):
    """Interface para analisadores de emoções."""

    @abstractmethod
    def analyze(self, texts: list[str]) -> dict[str, int]:
        """
        Analisa uma lista de textos e retorna contagem de emoções dominantes.
        Deve retornar um dicionário com chaves das 6 emoções básicas.
        """
        ...


class LexiconEmotionAnalyzer(EmotionAnalyzer):
    """Implementação baseada em léxico de emoções (~500 palavras)."""

    def __init__(self, lexicon: dict[str, dict[str, float]] | None = None):
        self.lexicon = lexicon or EMOTION_LEXICON

    def analyze(self, texts: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {e: 0 for e in EMOTIONS}

        for text in texts:
            text_lower = text.lower()
            scores: dict[str, float] = {e: 0.0 for e in EMOTIONS}

            for word, emotion_scores in self.lexicon.items():
                if word in text_lower:
                    for emotion, score in emotion_scores.items():
                        scores[emotion] += score

            max_score = max(scores.values())
            if max_score > 0:
                dominant = max(scores, key=scores.get)
                counts[dominant] += 1

        return counts
