from abc import ABC, abstractmethod
from collections import Counter
import re

from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.stopwords import PORTUGUESE_STOPWORDS


class TopicExtractor(ABC):
    """Interface para extratores de tópicos."""

    @abstractmethod
    def extract(self, texts: list[str], top_n: int = 10) -> list[dict]:
        """
        Extrai termos mais representativos de uma lista de textos.
        Retorna lista de dicts com 'term' e 'score'.
        """
        ...


class TfidfTopicExtractor(TopicExtractor):
    """Implementação usando TF-IDF via scikit-learn, com fallback para corpus pequeno."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words=list(PORTUGUESE_STOPWORDS),
            token_pattern=r'\b\w{2,}\b',   # palavras com 2+ caracteres
            max_df=1.0,                    # não remove termos frequentes em corpus pequeno
            min_df=1,                      # aparece em pelo menos 1 documento
            max_features=100,
            sublinear_tf=True,
        )

    def extract(self, texts: list[str], top_n: int = 10) -> list[dict]:
        if not texts:
            return []

        # Se houver poucas mensagens, usa fallback de frequência simples
        if len(texts) < 10:
            return self._fallback_frequency(texts, top_n)

        try:
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            feature_names = self.vectorizer.get_feature_names_out()

            # Soma os scores TF-IDF de cada termo em todos os documentos
            scores = tfidf_matrix.sum(axis=0).A1
            scored_terms = list(zip(feature_names, scores))
            scored_terms.sort(key=lambda x: x[1], reverse=True)

            return [
                {"term": term, "score": round(float(score), 4)}
                for term, score in scored_terms[:top_n]
                if score > 0
            ]
        except ValueError:
            # Se o TF-IDF falhar (ex.: vocabulário vazio), usa fallback
            return self._fallback_frequency(texts, top_n)

    def _fallback_frequency(self, texts: list[str], top_n: int) -> list[dict]:
        """Fallback: frequência simples quando há poucos dados."""
        words = []
        for text in texts:
            words.extend(re.findall(r'\b\w{2,}\b', text.lower()))
        words = [w for w in words if w not in PORTUGUESE_STOPWORDS]

        if not words:
            return []

        counter = Counter(words)
        total = sum(counter.values())
        return [
            {"term": word, "score": round(count / total, 4)}
            for word, count in counter.most_common(top_n)
        ]
