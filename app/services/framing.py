import re
from abc import ABC, abstractmethod

from app.core.framing_lexicon import FRAMING_LEXICON

FRAMING_CATEGORIES = ["ataque", "defesa", "ironia", "elogio", "pergunta", "neutro"]


class FramingAnalyzer(ABC):
    """Interface para analisadores de enquadramento discursivo."""

    @abstractmethod
    def analyze(self, texts: list[str]) -> dict[str, int]:
        """
        Analisa uma lista de textos e retorna contagem de
        ocorrências de cada categoria de framing.
        Deve retornar um dicionário com as chaves:
        'ataque', 'defesa', 'ironia', 'elogio', 'pergunta', 'neutro'.
        """
        ...


class LexiconFramingAnalyzer(FramingAnalyzer):
    """Implementação baseada em léxico de palavras/expressões de framing.

    O léxico mapeia palavras/expressões para listas de categorias associadas.
    Para cada texto, verifica a presença de palavras/expressões (case-insensitive)
    e conta a mensagem nas categorias correspondentes.
    Se um texto não corresponder a nenhuma categoria, conta como 'neutro'.
    """

    def __init__(self, lexicon: dict[str, list[str]] | None = None):
        self.lexicon = lexicon or FRAMING_LEXICON
        # Pré-compila padrões agrupados por categoria
        # O léxico tem formato: {palavra: [categoria1, categoria2, ...]}
        # Invertemos para: {categoria: [pattern1, pattern2, ...]}
        self._compiled: dict[str, list[re.Pattern]] = {c: [] for c in FRAMING_CATEGORIES if c != "neutro"}

        for word, categories in self.lexicon.items():
            if " " in word:
                # Expressão com espaços: busca por substring
                pattern_str = re.escape(word.lower())
            else:
                # Palavra simples: usa \b para borda de palavra
                pattern_str = r"\b" + re.escape(word.lower()) + r"\b"

            for cat in categories:
                if cat in self._compiled:
                    self._compiled[cat].append(re.compile(pattern_str, re.IGNORECASE))

    def analyze(self, texts: list[str]) -> dict[str, int]:
        counts: dict[str, int] = {c: 0 for c in FRAMING_CATEGORIES}

        for text in texts:
            matched_categories: set[str] = set()
            for category, patterns in self._compiled.items():
                for pattern in patterns:
                    if pattern.search(text):
                        matched_categories.add(category)
                        break  # uma correspondência por categoria basta

            if matched_categories:
                for cat in matched_categories:
                    counts[cat] += 1
            else:
                counts["neutro"] += 1

        return counts
