from collections import Counter
import re
from app.core.stopwords import PORTUGUESE_STOPWORDS
# from app.infrastructure.ml import get_sentiment_pipeline
from app.repositories.messages import create_message, list_messages_by_live
from sqlalchemy.orm import Session

class ChatService:
    def __init__(self, db: Session):
        self.db = db
        # self.sentiment_pipeline = get_sentiment_pipeline()

    def save_message(self, live_id: str, author: str, content: str):
        return create_message(self.db, live_id=live_id, author=author, content=content)

    def word_frequency(self, live_id: str, top_n: int = 10):
        messages = list_messages_by_live(self.db, live_id)
        if not messages:
            return None

        full_text = " ".join(msg.message for msg in messages)
        words = re.findall(r'\b\w+\b', full_text.lower())
        filtered = [w for w in words if w not in PORTUGUESE_STOPWORDS and not w.isdigit()]
        return Counter(filtered).most_common(top_n)

    def sentiment_summary(self, live_id: str):
        messages = list_messages_by_live(self.db, live_id)
        if not messages:
            return None

        texts = [msg.message for msg in messages]
        results = texts#self.sentiment_pipeline(texts)
        summary = {"Positivo": 0, "Negativo": 0, "Neutro": 0}
        label_map = {"1 star": "Negativo", "3 stars": "Neutro", "5 stars": "Positivo"}

        for result in results:
            summary[label_map.get(result["label"], "Neutro")] += 1

        return {
            "total": len(messages),
            "resumo": "test",
            "model": "lct-big-science/bertimbau-base-sentiment-analysis-portuguese",
        }