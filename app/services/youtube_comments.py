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
from app.core.timezone import to_local
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


def _parse_published_utc(published_str: str) -> datetime:
    """Converte string ISO da API (ex: '2024-01-01T00:00:00Z') para datetime UTC naive.

    Retorna datetime naive em UTC, pronto para armazenar no SQLite.
    """
    dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
    # Converte para UTC, depois remove tzinfo para SQLite
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.replace(tzinfo=None)


def _format_brt(dt: datetime | None) -> str | None:
    """Converte datetime UTC naive para string formatada em BRT.

    Se o datetime for None, retorna None.
    Se for naive, assume que está em UTC e converte para BRT.
    """
    if dt is None:
        return None
    # Assume que o valor armazenado é UTC naive
    dt_utc_aware = dt.replace(tzinfo=timezone.utc)
    dt_brt = to_local(dt_utc_aware)
    return dt_brt.isoformat()


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

    def fetch_comments(
        self, video_id: str, user_id: int, max_depth: int = -1
    ) -> dict[str, Any]:
        """Busca comentários de um vídeo e salva no banco.

        Args:
            video_id: ID do vídeo do YouTube.
            user_id: ID do usuário dono dos dados.
            max_depth: Profundidade máxima de respostas:
                -1 = todas (ilimitado)
                 0 = apenas comentários principais
                 1 = principal + respostas imediatas
                 2 = principal + N1 + N2
                etc.

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
                top_snippet = item["snippet"]["topLevelComment"]["snippet"]
                thread_id = item["id"]
                # reply_count REAL da API está no nível do thread, não no topLevelComment
                actual_reply_count = item["snippet"].get("totalReplyCount", 0)

                # Comentário principal (nível 0)
                comment = YouTubeComment(
                    video_id=video_id,
                    video_title=video_title,
                    author=top_snippet["authorDisplayName"],
                    comment=top_snippet["textDisplay"],
                    like_count=top_snippet.get("likeCount", 0),
                    reply_count=actual_reply_count,
                    is_reply=False,
                    reply_level=0,
                    parent_id=None,
                    published_at=_parse_published_utc(top_snippet["publishedAt"]),
                    user_id=user_id,
                )
                self.db.add(comment)
                total_comments += 1

                # Busca replies conforme profundidade
                if max_depth != 0 and actual_reply_count > 0:
                    replies = self._fetch_replies_recursive(
                        parent_id=thread_id,
                        parent_level=0,
                        video_id=video_id,
                        video_title=video_title,
                        user_id=user_id,
                        max_depth=max_depth,
                    )
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
            "max_depth": max_depth,
        }

    def _fetch_replies_recursive(
        self,
        parent_id: str,
        parent_level: int,
        video_id: str,
        video_title: str | None,
        user_id: int,
        max_depth: int = -1,
    ) -> int:
        """Busca replies recursivamente até max_depth.

        Args:
            parent_id: ID do comentário pai (thread_id ou comment_id).
            parent_level: Nível do comentário pai (0 = principal).
            video_id, video_title, user_id: metadados para salvar.
            max_depth: -1 = ilimitado, 0 = apenas principal, 1 = N1, etc.

        Retorna o número de replies salvas.
        """
        child_level = parent_level + 1

        # Verifica se deve parar
        if max_depth >= 0 and child_level > max_depth:
            return 0

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
                comment_id = item["id"]
                # Respostas não têm sub-respostas contadas pela API
                reply = YouTubeComment(
                    video_id=video_id,
                    video_title=video_title,
                    author=snippet["authorDisplayName"],
                    comment=snippet["textDisplay"],
                    like_count=snippet.get("likeCount", 0),
                    reply_count=0,
                    is_reply=True,
                    reply_level=child_level,
                    parent_id=parent_id,
                    published_at=_parse_published_utc(snippet["publishedAt"]),
                    user_id=user_id,
                )
                self.db.add(reply)
                count += 1

                # Recursão: busca respostas DESTA resposta
                # A API comments().list com parentId não retorna totalReplyCount,
                # então tentamos sempre buscar e paramos se vier vazio
                if max_depth == -1 or child_level < max_depth:
                    sub_replies = self._fetch_replies_recursive(
                        parent_id=comment_id,
                        parent_level=child_level,
                        video_id=video_id,
                        video_title=video_title,
                        user_id=user_id,
                        max_depth=max_depth,
                    )
                    count += sub_replies

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
                "collected_at": _format_brt(row.collected_at),
            }
            for row in rows
        ]

    def get_comments(self, video_id: str, user_id: int) -> list[dict[str, Any]]:
        """Retorna todos os comentários de um vídeo com datas em BRT."""
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
                "reply_level": c.reply_level,
                "parent_id": c.parent_id,
                "published_at": _format_brt(c.published_at),
                "collected_at": _format_brt(c.collected_at),
            }
            for c in comments
        ]

    def export_csv(self, video_id: str, user_id: int) -> bytes:
        """Exporta comentários para CSV."""
        comments = self.get_comments(video_id, user_id)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "author", "comment", "like_count", "reply_count",
            "is_reply", "reply_level", "published_at",
        ])

        for c in comments:
            writer.writerow([
                c["author"],
                c["comment"],
                c["like_count"],
                c["reply_count"],
                c["is_reply"],
                c["reply_level"],
                c["published_at"],
            ])

        return output.getvalue().encode("utf-8-sig")
