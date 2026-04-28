import csv
import io
import json

from app.core.stopwords import PORTUGUESE_STOPWORDS
from app.repositories.messages import list_messages_by_live
from app.services.sentiment import SentimentAnalyzer
from app.services.topics import TopicExtractor
from sqlalchemy.orm import Session


class ExportService:
    def __init__(self, db: Session, sentiment_analyzer: SentimentAnalyzer, topic_extractor: TopicExtractor | None = None):
        self.db = db
        self.sentiment_analyzer = sentiment_analyzer
        self.topic_extractor = topic_extractor

    def _get_messages(self, live_id: str, user_id: int | None = None):
        return list_messages_by_live(self.db, live_id, user_id=user_id)

    def export_json(self, live_id: str, include_analysis: bool = False, user_id: int | None = None) -> str:
        messages = self._get_messages(live_id, user_id)
        data = {
            "live_id": live_id,
            "messages": [
                {
                    "id": m.id,
                    "author": m.author,
                    "message": m.message,
                    "platform": m.platform,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        }
        if include_analysis and messages:
            texts = [m.message for m in messages]
            data["sentiment"] = self.sentiment_analyzer.analyze(texts)
            if self.topic_extractor:
                data["topics"] = self.topic_extractor.extract(texts)
        return json.dumps(data, indent=2, ensure_ascii=False)

    def export_csv(self, live_id: str, user_id: int | None = None) -> str:
        messages = self._get_messages(live_id, user_id)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "author", "message", "platform", "created_at"])
        for m in messages:
            writer.writerow([m.id, m.author, m.message, m.platform, m.created_at.isoformat() if m.created_at else ""])
        return output.getvalue()

    def export_xlsx(self, live_id: str, user_id: int | None = None) -> bytes:
        try:
            import openpyxl
        except ImportError:
            raise ImportError("openpyxl não está instalado. Execute: pip install openpyxl")

        messages = self._get_messages(live_id, user_id)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Mensagens"
        ws.append(["id", "author", "message", "platform", "created_at"])
        for m in messages:
            ws.append([m.id, m.author, m.message, m.platform, m.created_at.isoformat() if m.created_at else ""])
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()
