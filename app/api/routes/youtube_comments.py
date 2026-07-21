"""Rotas para coleta e consulta de comentários de vídeos do YouTube."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.chat import (
    YouTubeCommentResponse,
    YouTubeFetchResponse,
    YouTubeVideoListResponse,
    YouTubeVideoSummary,
)
from app.services.youtube_comments import YouTubeCommentService, extract_video_id

router = APIRouter(prefix="/youtube/comments", tags=["youtube-comments"])


@router.post("/fetch", response_model=YouTubeFetchResponse)
@limiter.limit("10/minute")
async def fetch_comments(
    request: Request,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dispara coleta de comentários de um vídeo do YouTube."""
    url_or_id = body.get("video_id", "")
    if not url_or_id:
        raise HTTPException(status_code=400, detail="video_id é obrigatório")

    video_id = extract_video_id(url_or_id)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="URL ou ID de vídeo inválido. Use um ID de 11 caracteres ou uma URL do YouTube.",
        )

    service = YouTubeCommentService(db)
    result = service.fetch_comments(video_id, current_user.id)
    return result


@router.get("", response_model=YouTubeVideoListResponse)
async def list_videos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista vídeos já coletados pelo usuário."""
    service = YouTubeCommentService(db)
    videos = service.list_videos(current_user.id)
    return YouTubeVideoListResponse(videos=videos)


@router.get("/{video_id}", response_model=list[YouTubeCommentResponse])
async def get_comments(
    video_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista comentários de um vídeo específico."""
    service = YouTubeCommentService(db)
    comments = service.get_comments(video_id, current_user.id)
    if not comments:
        raise HTTPException(
            status_code=404,
            detail="Nenhum comentário encontrado para este vídeo.",
        )
    return comments


@router.get("/{video_id}/export")
async def export_comments_csv(
    video_id: str,
    fmt: str = Query("csv", alias="format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta comentários para CSV."""
    if fmt != "csv":
        raise HTTPException(status_code=400, detail="Formato não suportado. Use 'csv'.")

    service = YouTubeCommentService(db)
    csv_bytes = service.export_csv(video_id, current_user.id)

    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=comentarios_{video_id}.csv",
        },
    )
