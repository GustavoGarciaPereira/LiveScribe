"""Serviço para coleta de comentários de vídeos do YouTube via Data API v3."""

import csv
import io
import re
from datetime import datetime, timezone
from typing import Any

from googleapiclient.discovery import build
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.youtube_comment import YouTubeComment


# Regex para extrair video_id de URLs do YouTube
YOUTUBE_URL_RE = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})"
)


def extract_video_id(url_or_id: str) -> str | None:
    """Extrai o video_id de uma URL do YouTube ou retorna o ID puro se for válido."""
    # Tenta extrair de URL
    match = YOUTUBE_URL_RE.search(url_or_id)
    if match:
        return match.group(1)
    # Se parece um ID válido (11 caracteres alfanuméricos + _-)
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url_or_id):
        return url_or_id
    return None


class YouTubeCommentService:
    """Gerencia a coleta e consulta de comentários do YouTube."""

    def __init__(self, db: Session):
        self.db = db
        self._youtube = None

    @property
    def youtube(self):
        if self._youtube is None:
            self._youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)
        return self._youtube

    def _get_video_title(self, video_id: str) -> str | None:
        """Obtém o título do vídeo via videos().list()."""
        try:
            request = self.youtube.videos().list(part="snippet", id=video_id)
            response = request.execute()
            items = response.get("items", [])
            if items:
                return items[0]["snippet"]["title"]
        except Exception:
            pass
        return None

    def fetch_comments(self, video_id: str, user_id: int) -> dict[str, Any]:
        """Busca todos os comentários de um vídeo e salva no banco.

        Retorna um resumo da coleta.
        """
        # Apaga dados anteriores do mesmo vídeo para este usuário
        self.db.query(YouTubeComment).filter(
            YouTubeComment.video_id == video_id,
            YouTubeComment.user_id == user_id,
        ).delete()
        self.db.commit()

        # Obtém o título do vídeo
        video_title = self._get_video_title(video_id)

        total_comments = 0
        total_replies = 0
        next_page_token = None

        while True:
            request = self.youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=100,
                pageToken=next_page_token,
                textFormat="plainText",
            )
            response = request.execute()

            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                thread_id = item["id"]

                # Comentário principal
                comment = YouTubeComment(
                    video_id=video_id,
                    video_title=video_title,
                    author=snippet["authorDisplayName"],
                    comment=snippet["textDisplay"],
                    like_count=snippet.get("likeCount", 0),
                    reply_count=snippet.get("totalReplyCount", 0),
                    is_reply=False,
                    parent_id=None,
                    published_at=datetime.fromisoformat(
                        snippet["publishedAt"].replace("Z", "+00:00")
                    ),
                    user_id=user_id,
                )
                self.db.add(comment)
                total_comments += 1

                # Busca replies se houver
                reply_count = snippet.get("totalReplyCount", 0)
                if reply_count > 0:
                    replies = self._fetch_replies(thread_id, video_id, video_title, user_id)
                    total_replies += replies

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        self.db.commit()

        return {
            "video_id": video_id,
            "video_title": video_title,
            "total_comments": total_comments,
            "total_replies": total_replies,
            "total_items": total_comments + total_replies,
        }

    def _fetch_replies(
        self,
        parent_id: str,
        video_id: str,
        video_title: str | None,
        user_id: int,
    ) -> int:
        """Busca replies de um comment thread."""
        count = 0
        next_page_token = None

        while True:
            request = self.youtube.comments().list(
                part="snippet",
                parentId=parent_id,
                maxResults=100,
                pageToken=next_page_token,
                textFormat="plainText",
            )
            response = request.execute()

            for item in response.get("items", []):
                snippet = item["snippet"]
                reply = YouTubeComment(
                    video_id=video_id,
                    video_title=video_title,
                    author=snippet["authorDisplayName"],
                    comment=snippet["textDisplay"],
                    like_count=snippet.get("likeCount", 0),
                    reply_count=0,
                    is_reply=True,
                    parent_id=parent_id,
                    published_at=datetime.fromisoformat(
                        snippet["publishedAt"].replace("Z", "+00:00")
                    ),
                    user_id=user_id,
                )
                self.db.add(reply)
                count += 1

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return count

    def list_videos(self, user_id: int) -> list[dict[str, Any]]:
        """Agrupa comentários por vídeo e retorna resumo."""
        rows = (
            self.db.query(
                YouTubeComment.video_id,
                YouTubeComment.video_title,
                YouTubeComment.collected_at,
                func.count(YouTubeComment.id).label("total_comments"),
            )
            .filter(
                YouTubeComment.user_id == user_id,
                YouTubeComment.is_reply == False,
            )
            .group_by(YouTubeComment.video_id)
            .order_by(func.max(YouTubeComment.collected_at).desc())
            .all()
        )

        return [
            {
                "video_id": row.video_id,
                "video_title": row.video_title,
                "total_comments": row.total_comments,
                "collected_at": row.collected_at.isoformat() if row.collected_at else None,
            }
            for row in rows
        ]

    def get_comments(self, video_id: str, user_id: int) -> list[dict[str, Any]]:
        """Retorna todos os comentários de um vídeo."""
        comments = (
            self.db.query(YouTubeComment)
            .filter(
                YouTubeComment.video_id == video_id,
                YouTubeComment.user_id == user_id,
            )
            .order_by(YouTubeComment.published_at.asc())
            .all()
        )

        return [
            {
                "id": c.id,
                "video_id": c.video_id,
                "video_title": c.video_title,
                "author": c.author,
                "comment": c.comment,
                "like_count": c.like_count,
                "reply_count": c.reply_count,
                "is_reply": c.is_reply,
                "parent_id": c.parent_id,
                "published_at": c.published_at.isoformat() if c.published_at else None,
                "collected_at": c.collected_at.isoformat() if c.collected_at else None,
            }
            for c in comments
        ]

    def export_csv(self, video_id: str, user_id: int) -> bytes:
        """Exporta comentários para CSV."""
        comments = self.get_comments(video_id, user_id)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["author", "comment", "like_count", "reply_count", "is_reply", "published_at"])

        for c in comments:
            writer.writerow([
                c["author"],
                c["comment"],
                c["like_count"],
                c["reply_count"],
                c["is_reply"],
                c["published_at"],
            ])

        return output.getvalue().encode("utf-8-sig")
