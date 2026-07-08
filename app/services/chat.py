from collections import Counter
from datetime import timedelta
import math
import re

from app.core.stopwords import PORTUGUESE_STOPWORDS
from app.core.timezone import to_local
from app.repositories.messages import create_message, list_messages_by_live, list_lives, list_top_authors
from app.services.sentiment import SentimentAnalyzer
from app.services.topics import TopicExtractor
from app.services.emojis import EmojiExtractor
from app.services.modality import ModalityAnalyzer
from app.services.emotion import EmotionAnalyzer
from sqlalchemy.orm import Session


class ChatService:
    def __init__(self, db: Session, sentiment_analyzer: SentimentAnalyzer, topic_extractor: TopicExtractor | None = None, emoji_extractor: EmojiExtractor | None = None, modality_analyzer: ModalityAnalyzer | None = None, emotion_analyzer: EmotionAnalyzer | None = None):
        self.db = db
        self.sentiment_analyzer = sentiment_analyzer
        self.topic_extractor = topic_extractor
        self.emoji_extractor = emoji_extractor
        self.modality_analyzer = modality_analyzer
        self.emotion_analyzer = emotion_analyzer

    @staticmethod
    def _bucket_messages(messages: list, interval_minutes: int) -> list[dict]:
        """Agrupa mensagens em buckets de intervalo fixo.

        Retorna lista de dicts com 'start', 'end' (datetime) e 'msgs' (list).
        Normaliza timestamps para timezone-aware (SQLite armazena como naive).
        """
        if not messages:
            return []

        first = to_local(messages[0].created_at)
        last = to_local(messages[-1].created_at)
        delta = timedelta(minutes=interval_minutes)

        # Normaliza todas as timestamps para evitar TypeError entre naive e aware
        msg_times = [to_local(m.created_at) for m in messages]

        buckets = []
        current = first
        while current <= last:
            buckets.append({"start": current, "end": current + delta, "msgs": []})
            current += delta

        for i, msg in enumerate(messages):
            msg_time = msg_times[i]
            for bucket in buckets:
                if bucket["start"] <= msg_time < bucket["end"]:
                    bucket["msgs"].append(msg)
                    break
            else:
                buckets[-1]["msgs"].append(msg)

        return buckets

    @staticmethod
    def _compute_statistics(compounds: list[float]) -> dict | None:
        """Calcula media, desvio padrao e IC 95% a partir de compound scores."""
        n = len(compounds)
        if n == 0:
            return None
        mean = sum(compounds) / n
        if n < 2:
            return {"mean": round(mean, 4), "std_dev": None, "ci_95": None}
        variance = sum((x - mean) ** 2 for x in compounds) / (n - 1)
        std_dev = math.sqrt(variance)
        margin = 1.96 * std_dev / math.sqrt(n)
        return {
            "mean": round(mean, 4),
            "std_dev": round(std_dev, 4),
            "ci_95": [round(mean - margin, 4), round(mean + margin, 4)],
        }

    @staticmethod
    def _get_compound_scores(analyzer, texts: list[str]) -> list[float]:
        """Extrai compound scores do analyzer via analyze_with_compound, se disponivel."""
        if not hasattr(analyzer, "analyze_with_compound"):
            return []
        try:
            result = analyzer.analyze_with_compound(texts)
            if isinstance(result, tuple) and len(result) == 2:
                return result[1]
        except (TypeError, ValueError):
            pass
        return []

    def list_lives(self, user_id: int | None = None) -> list[dict]:
        return list_lives(self.db, user_id=user_id)

    def save_message(self, live_id: str, author: str, content: str, platform: str = "youtube", user_id: int | None = None):
        return create_message(self.db, live_id=live_id, author=author, content=content, platform=platform, user_id=user_id)

    def word_frequency(self, live_id: str, top_n: int = 10, user_id: int | None = None):
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        if not messages:
            return None

        all_words = []
        for msg in messages:
            words = re.findall(r'\b\w+\b', msg.message.lower())
            words = [w for w in words if w not in PORTUGUESE_STOPWORDS]
            # Filtra URLs, digitos puros e tokens muito curtos
            words = [
                w for w in words
                if 'http' not in w
                and not w.isdigit()
                and len(w) >= 2
            ]
            all_words.extend(words)

        return Counter(all_words).most_common(top_n)

    def sentiment_summary(self, live_id: str, user_id: int | None = None) -> dict | None:
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        texts = [m.message for m in messages]

        if not texts:
            return None

        sentiments = self.sentiment_analyzer.analyze(texts)
        compounds = self._get_compound_scores(self.sentiment_analyzer, texts)
        statistics = self._compute_statistics(compounds)

        return {
            "model": "LeIA (VADER adaptado para português)",
            "sentiments": sentiments,
            "total_messages": len(texts),
            "statistics": statistics,
        }

    def sentiment_timeline(self, live_id: str, interval_minutes: int = 5, user_id: int | None = None, skip_empty: bool = True) -> dict | None:
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        if not messages:
            return None

        buckets = self._bucket_messages(messages, interval_minutes)

        timeline = []
        bucket_compounds: list[list[float]] = []
        for bucket in buckets:
            texts = [m.message for m in bucket["msgs"]]
            sentiments = self.sentiment_analyzer.analyze(texts) if texts else {"Positivo": 0, "Negativo": 0, "Neutro": 0}
            compounds = self._get_compound_scores(self.sentiment_analyzer, texts) if texts else []
            bucket_stats = self._compute_statistics(compounds)
            timeline.append({
                "start_time": bucket["start"],
                "end_time": bucket["end"],
                "total_messages": len(bucket["msgs"]),
                "sentiments": sentiments,
                "statistics": bucket_stats,
            })
            bucket_compounds.append(compounds)

        from scipy.stats import ttest_ind

        for i, entry in enumerate(timeline):
            if i == 0:
                entry["significant_change"] = False
                entry["p_value"] = None
                entry["change_direction"] = "none"
                entry["change_magnitude"] = None
                continue

            prev = bucket_compounds[i - 1]
            curr = bucket_compounds[i]

            if len(prev) < 2 or len(curr) < 2:
                entry["significant_change"] = False
                entry["p_value"] = None
                entry["change_direction"] = "none"
                entry["change_magnitude"] = None
                continue

            stat, p_val = ttest_ind(prev, curr, equal_var=False)
            p_value = float(round(p_val, 6))
            entry["p_value"] = p_value
            entry["significant_change"] = bool(p_value < 0.05)

            prev_mean = sum(prev) / len(prev)
            curr_mean = sum(curr) / len(curr)
            magnitude = float(round(curr_mean - prev_mean, 4))
            entry["change_magnitude"] = magnitude

            if magnitude > 0.05:
                entry["change_direction"] = "rise"
            elif magnitude < -0.05:
                entry["change_direction"] = "drop"
            else:
                entry["change_direction"] = "stable"

        # Remove buckets vazios (sem mensagens) para nao inflar contagem
        if skip_empty:
            timeline = [e for e in timeline if e["total_messages"] > 0]

        return {
            "live_id": live_id,
            "interval_minutes": interval_minutes,
            "timeline": timeline,
        }

    def engagement_peaks(self, live_id: str, top_n: int = 5, window_minutes: int = 1, user_id: int | None = None) -> dict | None:
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        if not messages:
            return None

        delta = timedelta(minutes=window_minutes)
        first = to_local(messages[0].created_at)
        last = to_local(messages[-1].created_at)

        # Normaliza todas as timestamps (SQLite armazena como naive)
        msg_times = [to_local(m.created_at) for m in messages]

        # Sliding window O(n): cada mensagem é visitada no máximo duas vezes
        window_counts: dict[str, int] = {}
        msg_idx = 0
        n = len(messages)
        current = first

        while current <= last:
            we = current + delta
            # Avança ponteiro além das mensagens que saíram da janela
            while msg_idx < n and msg_times[msg_idx] < current:
                msg_idx += 1
            # Conta mensagens dentro desta janela (ponteiro temporário não retrocede)
            count = 0
            temp = msg_idx
            while temp < n and msg_times[temp] < we:
                count += 1
                temp += 1
            window_counts[current.isoformat()] = count
            current += delta

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

    def topic_timeline(self, live_id: str, term: str, interval_minutes: int = 5, user_id: int | None = None) -> dict | None:
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        if not messages:
            return None

        buckets = self._bucket_messages(messages, interval_minutes)

        term_lower = term.lower()
        timeline = []
        for bucket in buckets:
            total = len(bucket["msgs"])
            count = sum(1 for m in bucket["msgs"] if term_lower in m.message.lower())
            timeline.append({
                "start_time": bucket["start"],
                "end_time": bucket["end"],
                "count": count,
                "total_messages": total,
            })

        return {
            "live_id": live_id,
            "term": term,
            "interval_minutes": interval_minutes,
            "timeline": timeline,
        }

    def extract_topics(self, live_id: str, top_n: int = 10, user_id: int | None = None) -> dict | None:
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        if not messages:
            return None

        if self.topic_extractor is None:
            return {"live_id": live_id, "topics": []}

        texts = [m.message for m in messages]
        topics = self.topic_extractor.extract(texts, top_n)
        return {"live_id": live_id, "topics": topics}

    def top_authors(self, live_id: str, top_n: int = 10, sort_by: str = "messages", user_id: int | None = None) -> dict | None:
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        if not messages:
            return None

        authors = list_top_authors(self.db, live_id, user_id=user_id, top_n=top_n)

        if not authors:
            return {"live_id": live_id, "total_authors": 0, "authors": []}

        # Calcula sentimento médio por autor (sentimento dominante)
        for author_data in authors:
            author_msgs = [m for m in messages if m.author == author_data["author"]]
            if author_msgs:
                sentiments = self.sentiment_analyzer.analyze([m.message for m in author_msgs])
                dominant = max(sentiments, key=sentiments.get)
                author_data["avg_sentiment"] = dominant
            else:
                author_data["avg_sentiment"] = "Neutro"

        if sort_by == "avg_sentiment":
            sentiment_order = {"Positivo": 0, "Neutro": 1, "Negativo": 2}
            authors.sort(key=lambda a: sentiment_order.get(a["avg_sentiment"], 1))

        # Conta total de autores distintos
        from sqlalchemy import func
        total = len(set(m.author for m in messages))

        return {
            "live_id": live_id,
            "total_authors": total,
            "authors": authors,
        }

    def get_questions(self, live_id: str, user_id: int | None = None, min_length: int = 10) -> dict | None:
        from app.services.questions import detect_questions

        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        if not messages:
            return None

        texts = [m.message for m in messages]
        questions = detect_questions(texts, min_length=min_length)

        return {
            "live_id": live_id,
            "questions": questions,
        }

    def modality_timeline(self, live_id: str, interval_minutes: int = 5, user_id: int | None = None) -> dict | None:
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        if not messages:
            return None

        buckets = self._bucket_messages(messages, interval_minutes)

        timeline = []
        default_counts = {"certeza": 0, "duvida": 0, "enfase": 0}
        for bucket in buckets:
            texts = [m.message for m in bucket["msgs"]]
            if self.modality_analyzer and texts:
                modality = self.modality_analyzer.analyze(texts)
            else:
                modality = default_counts
            timeline.append({
                "start_time": bucket["start"],
                "end_time": bucket["end"],
                "total_messages": len(bucket["msgs"]),
                "certeza": modality["certeza"],
                "duvida": modality["duvida"],
                "enfase": modality["enfase"],
            })

        return {
            "live_id": live_id,
            "interval_minutes": interval_minutes,
            "timeline": timeline,
        }

    def emotion_timeline(self, live_id: str, interval_minutes: int = 1, user_id: int | None = None) -> dict | None:
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        if not messages:
            return None

        buckets = self._bucket_messages(messages, interval_minutes)

        timeline = []
        default_counts = {"alegria": 0, "raiva": 0, "medo": 0, "surpresa": 0, "tristeza": 0, "nojo": 0}
        for bucket in buckets:
            texts = [m.message for m in bucket["msgs"]]
            if self.emotion_analyzer and texts:
                emotions = self.emotion_analyzer.analyze(texts)
            else:
                emotions = default_counts
            timeline.append({
                "start_time": bucket["start"],
                "end_time": bucket["end"],
                "total_messages": len(bucket["msgs"]),
                **emotions,
            })

        return {
            "live_id": live_id,
            "interval_minutes": interval_minutes,
            "timeline": timeline,
        }

    def emoji_analysis(self, live_id: str, top_n: int = 20, user_id: int | None = None) -> dict | None:
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        if not messages:
            return None

        if self.emoji_extractor is None:
            return {"live_id": live_id, "total_emojis": 0, "emojis": []}

        texts = [m.message for m in messages]
        emojis = self.emoji_extractor.extract_with_sentiment(texts, top_n)
        return {
            "live_id": live_id,
            "total_emojis": sum(e["count"] for e in emojis),
            "emojis": emojis,
        }

    def topic_sentiment(self, live_id: str, top_n: int = 10, user_id: int | None = None, video_id: str | None = None) -> dict | None:
        """Cruza tópicos com sentimento/emoção — 'o sentimento X é sobre qual assunto?'

        Se video_id for fornecido, enriquece cada tópico com o trecho transcrito
        do momento de pico (YouTube Transcript API).
        """
        messages = list_messages_by_live(self.db, live_id, user_id=user_id)
        if not messages:
            return None

        if self.topic_extractor is None:
            return {"live_id": live_id, "topics": []}

        texts = [m.message for m in messages]
        topics = self.topic_extractor.extract(texts, top_n)

        # Busca transcrição se video_id foi fornecido
        transcript = None
        from app.services.transcript import TranscriptService
        if video_id:
            transcript = TranscriptService.get_transcript(video_id)

        # Primeira mensagem como referência para elapsed time
        first_msg_time = to_local(messages[0].created_at)

        result_topics = []
        for topic in topics:
            term = topic["term"]
            # Filtra mensagens com palavra inteira (case-insensitive)
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            matching = [m for m in messages if pattern.search(m.message)]

            if not matching:
                continue

            matching_texts = [m.message for m in matching]

            # Sentimento
            sentiments = self.sentiment_analyzer.analyze(matching_texts)
            compounds = self._get_compound_scores(self.sentiment_analyzer, matching_texts)
            topic_stats = self._compute_statistics(compounds)

            # Emoção dominante
            dominant_emotion = "neutro"
            if self.emotion_analyzer:
                emotions = self.emotion_analyzer.analyze(matching_texts)
                if emotions and any(emotions.values()):
                    dominant_emotion = max(emotions, key=emotions.get)

            # Pico: minuto com mais mensagens (datetime arredondado para minuto)
            peak_minute_dt = None
            minute_counts: dict[str, int] = {}
            for m in matching:
                dt = to_local(m.created_at)
                minute_key = dt.replace(second=0, microsecond=0)
                minute_counts[minute_key] = minute_counts.get(minute_key, 0) + 1
            if minute_counts:
                peak_minute_dt = max(minute_counts, key=minute_counts.get)

            # peak_timestamp: segundos decorridos da primeira mensagem ate o pico
            peak_timestamp = None
            peak_minute = None
            if peak_minute_dt is not None:
                elapsed = (peak_minute_dt - first_msg_time).total_seconds()
                peak_timestamp = round(max(elapsed, 0), 1)
                # Formata como HH:MM:SS ou MM:SS (tempo decorrido)
                total_sec = int(elapsed)
                h, rem = divmod(total_sec, 3600)
                m, s = divmod(rem, 60)
                peak_minute = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

            # Trecho transcrito no pico
            transcript_snippet = None
            if transcript and peak_timestamp is not None:
                transcript_snippet = TranscriptService.find_snippet_at(transcript, peak_timestamp)

            result_topics.append({
                "topic": term,
                "message_count": len(matching),
                "sentiment": sentiments,
                "statistics": topic_stats,
                "dominant_emotion": dominant_emotion,
                "peak_minute": peak_minute,
                "transcript_snippet": transcript_snippet,
                "peak_timestamp": peak_timestamp,
            })

        # Ordena por message_count decrescente
        result_topics.sort(key=lambda t: t["message_count"], reverse=True)

        return {"live_id": live_id, "topics": result_topics}

