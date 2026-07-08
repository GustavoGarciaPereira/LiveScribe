from abc import ABC, abstractmethod


class SentimentAnalyzer(ABC):
    """Interface para analisadores de sentimento."""

    @abstractmethod
    def analyze(self, texts: list[str]) -> dict[str, int]:
        """
        Analisa uma lista de textos e retorna contagem de sentimentos.
        Deve retornar um dicionário com chaves 'Positivo', 'Negativo', 'Neutro'.
        """
        ...


class LeiaSentimentAnalyzer(SentimentAnalyzer):
    """Implementação usando o léxico LeIA (VADER adaptado para português)."""

    def __init__(self):
        from LeIA import SentimentIntensityAnalyzer
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze(self, texts: list[str]) -> dict[str, int]:
        counts = {"Positivo": 0, "Negativo": 0, "Neutro": 0}

        for text in texts:
            scores = self.analyzer.polarity_scores(text)
            compound = scores["compound"]
            if compound >= 0.05:
                counts["Positivo"] += 1
            elif compound <= -0.05:
                counts["Negativo"] += 1
            else:
                counts["Neutro"] += 1

        return counts

    def analyze_with_compound(self, texts: list[str]) -> tuple[dict[str, int], list[float]]:
        """Analisa sentimentos e retorna (counts, lista de compound scores)."""
        counts = {"Positivo": 0, "Negativo": 0, "Neutro": 0}
        compounds: list[float] = []

        for text in texts:
            scores = self.analyzer.polarity_scores(text)
            compound = scores["compound"]
            compounds.append(compound)
            if compound >= 0.05:
                counts["Positivo"] += 1
            elif compound <= -0.05:
                counts["Negativo"] += 1
            else:
                counts["Neutro"] += 1

        return counts, compounds
