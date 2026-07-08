import base64
import io
import json
from collections import Counter
from datetime import datetime

from app.core.timezone import now as now_local

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from app.repositories.messages import list_messages_by_live
from app.services.chat import ChatService


class ReportService:
    def __init__(self, chat_service: ChatService):
        self.chat_service = chat_service
        self.db = chat_service.db

    def generate_pdf(self, live_id: str, user_id: int | None = None) -> bytes:
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)

        sentiment = self.chat_service.sentiment_summary(live_id, user_id=user_id)
        word_freq = self.chat_service.word_frequency(live_id, top_n=15, user_id=user_id) or []
        peaks_result = self.chat_service.engagement_peaks(live_id, top_n=10, user_id=user_id)
        topics = self.chat_service.extract_topics(live_id, top_n=10, user_id=user_id)
        topic_sentiment = self.chat_service.topic_sentiment(live_id, top_n=10, user_id=user_id, video_id=live_id)
        authors = self.chat_service.top_authors(live_id, top_n=10, user_id=user_id)
        questions = self.chat_service.get_questions(live_id, user_id=user_id, min_length=10)
        modality = self.chat_service.modality_timeline(live_id, interval_minutes=5, user_id=user_id)
        emotions = self.chat_service.emotion_timeline(live_id, interval_minutes=1, user_id=user_id)
        emojis = self.chat_service.emoji_analysis(live_id, top_n=20, user_id=user_id)
        sentiment_timeline = self.chat_service.sentiment_timeline(live_id, interval_minutes=5, user_id=user_id)
        # Garantir que sentiment_timeline seja dict (pode vir como JSON string em alguns setups)
        if isinstance(sentiment_timeline, str):
            sentiment_timeline = json.loads(sentiment_timeline)

        timeline = sentiment_timeline.get("timeline", []) if sentiment_timeline else []
        if not isinstance(timeline, list):
            timeline = []

        total_messages = len(messages)
        unique_authors = len(set(m.author for m in messages)) if messages else 0

        if messages:
            first_msg = messages[0].created_at
            last_msg = messages[-1].created_at
            duration = str(last_msg - first_msg).split(".")[0]
        else:
            first_msg = None
            last_msg = None
            duration = "0:00:00"

        charts = self._generate_charts(sentiment, emotions, modality, peaks_result)

        sentiment_summary = sentiment["sentiments"] if sentiment else {"Positivo": 0, "Negativo": 0, "Neutro": 0}

        context = {
            "live_id": live_id,
            "total_messages": total_messages,
            "unique_authors": unique_authors,
            "first_msg": first_msg.strftime("%d/%m/%Y %H:%M") if first_msg else "N/D",
            "last_msg": last_msg.strftime("%d/%m/%Y %H:%M") if last_msg else "N/D",
            "duration": duration,
            "sentiment_summary": sentiment_summary,
            "word_freq": word_freq,
            "topics": topics.get("topics", []) if topics else [],
            "topic_sentiment": topic_sentiment.get("topics", []) if topic_sentiment else [],
            "authors": authors.get("authors", []) if authors else [],
            "questions": questions.get("questions", []) if questions else [],
            "emojis": emojis.get("emojis", []) if emojis else [],
            "sentiment_timeline": timeline,
            "total_intervals": len(timeline),
            "charts": charts,
            "generated_at": now_local().strftime("%d/%m/%Y %H:%M BRT"),
        }

        from app.templates.report_html import report_html
        html = report_html.render(context)

        from weasyprint import HTML
        return HTML(string=html).write_pdf()

    def _generate_charts(self, sentiment, emotions, modality, peaks) -> dict[str, str]:
        charts = {}

        if sentiment and sentiment.get("timeline"):
            charts["sentiment"] = self._line_chart(
                sentiment["timeline"],
                ["Positivo", "Negativo", "Neutro"],
                ["#22c55e", "#ef4444", "#94a3b8"],
                "Sentimentos ao longo do tempo",
            )

        if emotions and emotions.get("timeline"):
            charts["emotions"] = self._line_chart(
                emotions["timeline"],
                ["alegria", "raiva", "medo", "surpresa", "tristeza", "nojo"],
                ["#22c55e", "#ef4444", "#6366f1", "#fbbf24", "#3b82f6", "#84cc16"],
                "Emoções ao longo do tempo",
            )

        if modality and modality.get("timeline"):
            charts["modality"] = self._line_chart(
                modality["timeline"],
                ["certeza", "duvida", "enfase"],
                ["#22c55e", "#f97316", "#a855f7"],
                "Modalidade ao longo do tempo",
            )

        if peaks and peaks.get("peaks"):
            charts["peaks"] = self._bar_chart(
                peaks["peaks"], "time", "message_count", "#f97316",
                "Picos de engajamento",
            )

        return charts

    def _line_chart(self, timeline, keys, colors, title) -> str:
        fig, ax = plt.subplots(figsize=(8, 3))
        labels = [b["start_time"].strftime("%H:%M") if isinstance(b["start_time"], datetime)
                   else b["start_time"][:16] for b in timeline]

        for i, key in enumerate(keys):
            values = [b[key] if isinstance(b, dict) else b.get(key, 0) for b in timeline]
            ax.plot(labels, values, color=colors[i % len(colors)], linewidth=1.5, label=key.capitalize())

        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.legend(fontsize=7, loc="upper right")
        ax.tick_params(axis="x", rotation=45, labelsize=7)
        ax.tick_params(axis="y", labelsize=7)
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120)
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()

    def _bar_chart(self, data, x_key, y_key, color, title) -> str:
        fig, ax = plt.subplots(figsize=(8, 3))
        labels = [d[x_key].strftime("%H:%M") if isinstance(d[x_key], datetime)
                   else str(d[x_key])[:16] for d in data]
        values = [d[y_key] for d in data]

        ax.bar(labels, values, color=color, width=0.6)
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.tick_params(axis="x", rotation=45, labelsize=7)
        ax.tick_params(axis="y", labelsize=7)
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120)
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
