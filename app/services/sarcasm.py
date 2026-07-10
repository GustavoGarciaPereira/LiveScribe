import re
from abc import ABC, abstractmethod

from app.core.sarcasm_lexicon import SARCASM_LEXICON


class SarcasmAnalyzer(ABC):
    """Interface para analisadores de sarcasmo/ironia."""

    @abstractmethod
    def analyze(self, texts: list[str]) -> dict[str, int]:
        """
        Analisa uma lista de textos e retorna contagem de
        mensagens sarcásticas e não-sarcásticas.
        Deve retornar um dicionário com as chaves 'sarcastic' e 'non_sarcastic'.
        """
        ...


class LexiconSarcasmAnalyzer(SarcasmAnalyzer):
    """Implementação baseada em léxico de expressões irônicas.

    Para cada texto, verifica a presença de expressões do léxico
    usando busca case-insensitive (substring ou \b conforme o caso).
    Se uma ou mais expressões forem encontradas, a mensagem conta
    como sarcástica.
    """

    def __init__(self, lexicon: list[str] | None = None):
        self.lexicon = lexicon or SARCASM_LEXICON
        # Pré-compila os padrões
        self._patterns: list[re.Pattern] = []
        for expr in self.lexicon:
            if " " in expr:
                # Expressão com espaços: busca por substring
                pattern_str = re.escape(expr.lower())
            else:
                # Palavra ou risada curta: usa \b para borda de palavra
                pattern_str = r"\b" + re.escape(expr.lower()) + r"\b"
            self._patterns.append(re.compile(pattern_str, re.IGNORECASE))

    def analyze(self, texts: list[str]) -> dict[str, int]:
        sarcastic = 0
        non_sarcastic = 0

        for text in texts:
            is_sarcastic = False
            for pattern in self._patterns:
                if pattern.search(text):
                    is_sarcastic = True
                    break
            if is_sarcastic:
                sarcastic += 1
            else:
                non_sarcastic += 1

        return {"sarcastic": sarcastic, "non_sarcastic": non_sarcastic}
