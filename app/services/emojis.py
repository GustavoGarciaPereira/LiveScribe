from abc import ABC, abstractmethod
from collections import Counter

import regex

from app.core.emoji_sentiment import EMOJI_SENTIMENT_MAP


class EmojiExtractor(ABC):
    """Interface para extratores de emojis."""

    @abstractmethod
    def extract_with_sentiment(self, texts: list[str], top_n: int = 20) -> list[dict]:
        """
        Extrai emojis de uma lista de textos, conta ocorrências e mapeia sentimento.
        Retorna lista de dicts com 'emoji', 'count' e 'sentiment'.
        """
        ...


class RegexEmojiExtractor(EmojiExtractor):
    """Extrai emojis usando regex Extended_Pictographic e mapeia sentimento por dicionario."""

    def __init__(self):
        self.pattern = regex.compile(r'\p{Extended_Pictographic}')

    def extract_with_sentiment(self, texts: list[str], top_n: int = 20) -> list[dict]:
        all_emojis: list[str] = []
        for text in texts:
            all_emojis.extend(self.pattern.findall(text))

        if not all_emojis:
            return []

        counter = Counter(all_emojis)
        result = []
        for emoji_char, count in counter.most_common(top_n):
            sentiment = EMOJI_SENTIMENT_MAP.get(emoji_char, "Neutro")
            result.append({
                "emoji": emoji_char,
                "count": count,
                "sentiment": sentiment,
            })
        return result