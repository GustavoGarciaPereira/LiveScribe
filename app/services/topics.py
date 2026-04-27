from abc import ABC, abstractmethod

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
    """Implementação usando TF-IDF via scikit-learn."""

    def extract(self, texts: list[str], top_n: int = 10) -> list[dict]:
        if not texts:
            return []

        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(
            stop_words=PORTUGUESE_STOPWORDS,
            sublinear_tf=True,
            max_features=100,
            token_pattern=r'\b\w+\b',
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
        except ValueError:
            # Se todos os termos são stopwords ou textos vazios
            return []

        # Soma os scores de cada termo em todos os documentos
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.sum(axis=0).A1  # array 1D

        # Ordena por score decrescente
        ranked = sorted(
            zip(feature_names, scores), key=lambda x: x[1], reverse=True
        )[:top_n]

        return [{"term": term, "score": round(float(score), 4)} for term, score in ranked if score > 0]
