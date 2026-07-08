"""Serviço de transcrição de vídeos do YouTube.

Usa a YouTube Transcript API (gratuita, sem autenticação) para obter
legendas/transcrições automáticas. Cacheia resultados para evitar
chamadas repetidas ao mesmo vídeo.
"""

import logging
from functools import lru_cache

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)


class TranscriptService:
    """Obtém e cacheia transcrições de vídeos do YouTube."""

    @staticmethod
    @lru_cache(maxsize=32)
    def get_transcript(video_id: str) -> list[dict] | None:
        """Retorna a transcrição como lista de trechos ou None se indisponível.

        Cada trecho: {"text": str, "start": float (segundos), "duration": float}
        """
        try:
            api = YouTubeTranscriptApi()
            result = api.fetch(video_id, languages=("pt", "en"))
            transcript = result.to_raw_data()
            logger.info(f"Transcript obtida para video={video_id} ({len(transcript)} trechos).")
            return transcript
        except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as e:
            logger.warning(f"Transcript indisponível para video={video_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado na transcript para video={video_id}: {e}")
            return None

    @staticmethod
    def find_snippet_at(transcript: list[dict], timestamp_seconds: float, context_radius: float = 15.0) -> str | None:
        """Encontra o trecho transcrito mais próximo de um timestamp.

        Retorna uma janela de ~30s ao redor do ponto, concatenando trechos adjacentes.
        Retorna None se transcript for vazio ou timestamp_seconds for None.
        """
        if not transcript or timestamp_seconds is None:
            return None

        # Encontra o trecho mais próximo do timestamp
        closest = min(transcript, key=lambda t: abs(t["start"] - timestamp_seconds))

        # Coleta trechos em uma janela ao redor
        window_start = closest["start"] - context_radius
        window_end = closest["start"] + context_radius + closest.get("duration", 0)

        snippet_parts = []
        for t in transcript:
            if window_start <= t["start"] <= window_end:
                snippet_parts.append(t["text"])

        if not snippet_parts:
            return closest["text"]

        return " ".join(snippet_parts)
