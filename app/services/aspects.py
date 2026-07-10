import re
from abc import ABC, abstractmethod

from app.core.aspects_lexicon import ASPECTS_LEXICON
from app.services.sentiment import LeiaSentimentAnalyzer


class AspectAnalyzer(ABC):
    """Interface para analisadores de sentimento baseado em aspectos."""

    @abstractmethod
    def analyze(self, texts: list[str], entities: list[str] | None = None) -> dict[str, dict]:
        """
        Analisa uma lista de textos e retorna o sentimento agregado
        para cada entidade encontrada.

        Retorna um dicionário no formato:
            { "entidade": {"messages": int, "sentiment": {"Positivo": int, "Negativo": int, "Neutro": int}} }
        """
        ...


class LexiconAspectAnalyzer(AspectAnalyzer):
    """Implementação baseada em léxico de entidades + LeIA para sentimento.

    Para cada texto, verifica a presença de cada entidade (case-insensitive).
    Coleta as mensagens associadas a cada entidade e calcula o sentimento
    agregado usando LeiaSentimentAnalyzer.
    """

    def __init__(self, lexicon: dict[str, list[str]] | None = None, sentiment_analyzer=None):
        self.lexicon = lexicon or ASPECTS_LEXICON
        self.sentiment_analyzer = sentiment_analyzer or LeiaSentimentAnalyzer()
        # Pré-compila padrões para cada entidade
        self._compiled: dict[str, list[re.Pattern]] = {}
        for entity, variations in self.lexicon.items():
            patterns = []
            for var in variations:
                if " " in var:
                    pattern_str = re.escape(var.lower())
                else:
                    pattern_str = r"\b" + re.escape(var.lower()) + r"\b"
                patterns.append(re.compile(pattern_str, re.IGNORECASE))
            self._compiled[entity] = patterns

    def _find_entities(self, text: str) -> set[str]:
        """Retorna o conjunto de entidades mencionadas em um texto."""
        found: set[str] = set()
        for entity, patterns in self._compiled.items():
            for pattern in patterns:
                if pattern.search(text):
                    found.add(entity)
                    break
        return found

    def analyze(self, texts: list[str], entities: list[str] | None = None) -> dict[str, dict]:
        allowed = set(entities) if entities else set(self._compiled.keys())

        # Agrupa mensagens por entidade
        entity_texts: dict[str, list[str]] = {e: [] for e in allowed}

        for text in texts:
            found = self._find_entities(text)
            for entity in found:
                if entity in allowed:
                    entity_texts[entity].append(text)

        # Calcula sentimento para cada entidade
        result: dict[str, dict] = {}
        for entity, msgs in entity_texts.items():
            if not msgs:
                result[entity] = {"messages": 0, "sentiment": {"Positivo": 0, "Negativo": 0, "Neutro": 0}}
            else:
                sentiment = self.sentiment_analyzer.analyze(msgs)
                result[entity] = {"messages": len(msgs), "sentiment": sentiment}

        return result
