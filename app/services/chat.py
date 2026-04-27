from collections import Counter
from datetime import timedelta
import re

from app.core.stopwords import PORTUGUESE_STOPWORDS
from app.repositories.messages import create_message, list_messages_by_live, list_lives
from app.services.sentiment import SentimentAnalyzer
from app.services.topics import TopicExtractor
from sqlalchemy.orm import Session


class ChatService:
    def __init__(self, db: Session, sentiment_analyzer: SentimentAnalyzer, topic_extractor: TopicExtractor | None = None):
        self.db = db
        self.sentiment_analyzer = sentiment_analyzer
        self.topic_extractor = topic_extractor

    def list_lives(self) -> list[dict]:
        return list_lives(self.db)

    def save_message(self, live_id: str, author: str, content: str, platform: str = "youtube"):
        return create_message(self.db, live_id=live_id, author=author, content=content, platform=platform)

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

    def sentiment_summary(self, live_id: str) -> dict | None:
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

    def sentiment_timeline(self, live_id: str, interval_minutes: int = 5) -> dict | None:
        messages = list_messages_by_live(self.db, live_id)
        if not messages:
            return None

        first = messages[0].created_at
        last = messages[-1].created_at
        delta = timedelta(minutes=interval_minutes)

        # Gera buckets
        buckets = []
        current = first
        while current <= last:
            buckets.append({"start": current, "end": current + delta, "msgs": []})
            current += delta

        # Distribui mensagens nos buckets
        for msg in messages:
            for bucket in buckets:
                if bucket["start"] <= msg.created_at < bucket["end"]:
                    bucket["msgs"].append(msg)
                    break
            else:
                # Garante que a última mensagem cai no último bucket
                buckets[-1]["msgs"].append(msg)

        # Analisa cada bucket
        timeline = []
        for bucket in buckets:
            texts = [m.message for m in bucket["msgs"]]
            sentiments = self.sentiment_analyzer.analyze(texts) if texts else {"Positivo": 0, "Negativo": 0, "Neutro": 0}
            timeline.append({
                "start_time": bucket["start"],
                "end_time": bucket["end"],
                "total_messages": len(bucket["msgs"]),
                "sentiments": sentiments,
            })

        return {
            "live_id": live_id,
            "interval_minutes": interval_minutes,
            "timeline": timeline,
        }

    def engagement_peaks(self, live_id: str, top_n: int = 5, window_minutes: int = 1) -> dict | None:
        messages = list_messages_by_live(self.db, live_id)
        if not messages:
            return None

        delta = timedelta(minutes=window_minutes)
        first = messages[0].created_at
        last = messages[-1].created_at

        # Conta mensagens por janela
        window_counts: dict[str, int] = {}
        current = first
        while current <= last:
            key = current.isoformat()
            window_counts[key] = 0
            for msg in messages:
                if current <= msg.created_at < current + delta:
                    window_counts[key] += 1
            current += delta

        # Ordena pelos picos
        sorted_peaks = sorted(window_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
        from datetime import datetime as dt
        peaks = [
            {"time": dt.fromisoformat(t), "message_count": c}
            for t, c in sorted_peaks if c > 0
        ]

        return {
            "live_id": live_id,
            "window_minutes": window_minutes,
            "peaks": peaks,
        }

    def extract_topics(self, live_id: str, top_n: int = 10) -> dict | None:
        messages = list_messages_by_live(self.db, live_id)
        if not messages:
            return None

        if self.topic_extractor is None:
            return {"live_id": live_id, "topics": []}

        texts = [m.message for m in messages]
        topics = self.topic_extractor.extract(texts, top_n)
        return {"live_id": live_id, "topics": topics}
