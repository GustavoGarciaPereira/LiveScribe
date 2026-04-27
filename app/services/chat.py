from collections import Counter
import re
from typing import Optional

from app.core.stopwords import PORTUGUESE_STOPWORDS
from app.repositories.messages import create_message, list_messages_by_live
from app.services.sentiment import SentimentAnalyzer
from sqlalchemy.orm import Session


class ChatService:
    def __init__(self, db: Session, sentiment_analyzer: SentimentAnalyzer):
        self.db = db
        self.sentiment_analyzer = sentiment_analyzer

    def save_message(self, live_id: str, author: str, content: str):
        return create_message(self.db, live_id=live_id, author=author, content=content)

    def word_frequency(self, live_id: str, top_n: int = 10):
        messages = list_messages_by_live(self.db, live_id)
        if not messages:
            return None

        all_words = []
        for msg in messages:
            words = re.findall(r'\b\w+\b', msg.message.lower())
            words = [w for w in words if w not in PORTUGUESE_STOPWORDS]
            all_words.extend(words)

        return Counter(all_words).most_common(top_n)

    def sentiment_summary(self, live_id: str) -> Optional[dict]:
        messages = list_messages_by_live(self.db, live_id)
        texts = [m.message for m in messages]

        if not texts:
            return None

        sentiments = self.sentiment_analyzer.analyze(texts)

        return {
            "model": "LeIA (VADER adaptado para português)",
            "sentiments": sentiments,
            "total_messages": len(texts),
        }
