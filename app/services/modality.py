import re
from abc import ABC, abstractmethod

from app.core.modality_lexicon import MODALITY_LEXICON


class ModalityAnalyzer(ABC):
    """Interface para analisadores de modalização do discurso."""

    @abstractmethod
    def analyze(self, texts: list[str]) -> dict[str, int]:
        """
        Analisa uma lista de textos e retorna contagem de
        ocorrências de cada categoria de modalização.
        Deve retornar um dicionário com chaves 'certeza', 'duvida', 'enfase'.
        """
        ...


class LexiconModalityAnalyzer(ModalityAnalyzer):
    """Implementação baseada em dicionário léxico de modalização."""

    def __init__(self, lexicon: dict[str, list[str]] | None = None):
        self.lexicon = lexicon or MODALITY_LEXICON

    def analyze(self, texts: list[str]) -> dict[str, int]:
        counts = {"certeza": 0, "duvida": 0, "enfase": 0}

        for text in texts:
            text_lower = text.lower()
            for category, expressions in self.lexicon.items():
                for expr in expressions:
                    pattern = re.escape(expr.lower())
                    occurrences = len(re.findall(pattern, text_lower))
                    counts[category] += occurrences

        return counts
