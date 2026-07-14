import logging
from urllib.parse import quote
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from app.models.user import User
from app.schemas.chat import (
    ChatMessage, MessageResponse, WordFrequencyItem, WordFrequencyResponse,
    SentimentResponse, LiveSummary, LiveListResponse,
    SentimentTimelineResponse, TimelineBucket,
    EngagementPeaksResponse, EngagementPeak,
    TopicsResponse, TopicItem,
    TopicTimelineResponse, TopicBucket,
    TopicSentimentResponse, TopicSentimentItem,
    EmojiResponse, EmojiItem,
    TopAuthorsResponse, AuthorItem,
    QuestionsResponse, QuestionItem,
    ModalityTimelineResponse, ModalityBucket,
    EmotionTimelineResponse, EmotionBucket,
    FramingResponse,
    SarcasmResponse,
    AspectSentimentResponse,
)
from app.api.deps import get_chat_service, get_current_user
from app.core.limiter import limiter
from app.repositories.messages import list_messages_by_live
from app.services.chat import ChatService
from app.services.webhook import trigger_webhooks

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages", response_model=MessageResponse)
@limiter.limit("1600/minute")
def save_message(
    request: Request,
    payload: ChatMessage,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    message = service.save_message(
        payload.live_id, payload.author, payload.message,
        payload.platform or "youtube",
        user_id=user.id,
    )
    background_tasks.add_task(trigger_webhooks, service.db, "new_message", {
        "live_id": message.live_id,
        "author": message.author,
        "message": message.message,
        "platform": message.platform,
    }, user_id=user.id)
    return MessageResponse.model_validate(message)


@router.get("/lives", response_model=LiveListResponse)
def list_lives_endpoint(
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    lives = service.list_lives(user_id=user.id)
    return LiveListResponse(
        lives=[LiveSummary(**live) for live in lives],
        total_lives=len(lives),
    )


@router.get("/{live_id}/word-frequency", response_model=WordFrequencyResponse)
def word_frequency(
    live_id: str,
    top_n: int = Query(10, ge=1, le=500),
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    freq_tuples = service.word_frequency(live_id, top_n, user_id=user.id)
    if not freq_tuples:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    items = [
        WordFrequencyItem(palavra=word, frequencia=count)
        for word, count in freq_tuples
    ]
    return WordFrequencyResponse(live_id=live_id, word_frequency=items)


@router.get("/{live_id}/sentiment", response_model=SentimentResponse)
def sentiment_analysis(
    live_id: str,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    try:
        summary = service.sentiment_summary(live_id, user_id=user.id)
    except Exception as e:
        logger.error(f"Sentiment analysis failed for live_id={live_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno ao processar análise.")
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return SentimentResponse(
        live_id=live_id,
        total_messages_analyzed=summary["total_messages"],
        sentiment_summary=summary["sentiments"],
        statistics=summary.get("statistics"),
        library_used="Hugging Face Transformers",
        model=summary["model"],
    )


@router.get("/{live_id}/sentiment-timeline", response_model=SentimentTimelineResponse)
def sentiment_timeline(
    live_id: str,
    interval_minutes: int = Query(5, ge=1, le=1440),
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    result = service.sentiment_timeline(live_id, interval_minutes, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return SentimentTimelineResponse(
        live_id=result["live_id"],
        interval_minutes=result["interval_minutes"],
        timeline=[TimelineBucket(**bucket) for bucket in result["timeline"]],
    )


@router.get("/{live_id}/engagement-peaks", response_model=EngagementPeaksResponse)
def engagement_peaks(
    live_id: str,
    background_tasks: BackgroundTasks,
    top_n: int = Query(5, ge=1, le=500),
    window_minutes: int = Query(1, ge=1, le=60),
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    result = service.engagement_peaks(live_id, top_n, window_minutes, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    background_tasks.add_task(trigger_webhooks, service.db, "peak_engagement", result, user_id=user.id)
    return EngagementPeaksResponse(
        live_id=result["live_id"],
        window_minutes=result["window_minutes"],
        peaks=[EngagementPeak(**peak) for peak in result["peaks"]],
    )


@router.get("/{live_id}/topics", response_model=TopicsResponse)
def topics(
    live_id: str,
    top_n: int = Query(10, ge=1, le=500),
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    result = service.extract_topics(live_id, top_n, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return TopicsResponse(
        live_id=result["live_id"],
        topics=[TopicItem(**t) for t in result["topics"]],
    )


@router.get("/{live_id}/topic-timeline", response_model=TopicTimelineResponse)
def topic_timeline(
    live_id: str,
    term: str,
    interval_minutes: int = Query(5, ge=1, le=1440),
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    result = service.topic_timeline(live_id, term, interval_minutes, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return TopicTimelineResponse(
        live_id=result["live_id"],
        term=result["term"],
        interval_minutes=result["interval_minutes"],
        timeline=[TopicBucket(**bucket) for bucket in result["timeline"]],
    )


@router.get("/{live_id}/top-authors", response_model=TopAuthorsResponse)
def top_authors(
    live_id: str,
    top_n: int = Query(10, ge=1, le=500),
    sort_by: str = "messages",
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    result = service.top_authors(live_id, top_n, sort_by, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return TopAuthorsResponse(
        live_id=result["live_id"],
        total_authors=result["total_authors"],
        authors=[AuthorItem(**a) for a in result["authors"]],
    )


@router.get("/{live_id}/emojis", response_model=EmojiResponse)
def emoji_analysis(
    live_id: str,
    top_n: int = Query(20, ge=1, le=500),
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    result = service.emoji_analysis(live_id, top_n, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return EmojiResponse(
        live_id=result["live_id"],
        total_emojis=result["total_emojis"],
        emojis=[EmojiItem(**e) for e in result["emojis"]],
    )


@router.get("/{live_id}/questions", response_model=QuestionsResponse)
def questions(
    live_id: str,
    min_length: int = Query(10, ge=1, le=500),
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    result = service.get_questions(live_id, user_id=user.id, min_length=min_length)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return QuestionsResponse(
        live_id=result["live_id"],
        questions=[QuestionItem(**q) for q in result["questions"]],
    )


@router.get("/{live_id}/emotion-timeline", response_model=EmotionTimelineResponse)
def emotion_timeline(
    live_id: str,
    interval_minutes: int = Query(1, ge=1, le=1440),
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    result = service.emotion_timeline(live_id, interval_minutes, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return EmotionTimelineResponse(
        live_id=result["live_id"],
        interval_minutes=result["interval_minutes"],
        timeline=[EmotionBucket(**bucket) for bucket in result["timeline"]],
    )


@router.get("/{live_id}/modality-timeline", response_model=ModalityTimelineResponse)
def modality_timeline(
    live_id: str,
    interval_minutes: int = Query(5, ge=1, le=1440),
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    result = service.modality_timeline(live_id, interval_minutes, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return ModalityTimelineResponse(
        live_id=result["live_id"],
        interval_minutes=result["interval_minutes"],
        timeline=[ModalityBucket(**bucket) for bucket in result["timeline"]],
    )


@router.get("/{live_id}/framing", response_model=FramingResponse)
def framing_analysis(
    live_id: str,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    result = service.framing_analysis(live_id, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return FramingResponse(
        live_id=result["live_id"],
        total_messages=result["total_messages"],
        framing=result["framing"],
    )


@router.get("/{live_id}/sarcasm", response_model=SarcasmResponse)
def sarcasm_analysis(
    live_id: str,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    result = service.sarcasm_analysis(live_id, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return SarcasmResponse(
        live_id=result["live_id"],
        total_messages=result["total_messages"],
        sarcasm=result["sarcasm"],
    )


@router.get("/{live_id}/aspect-sentiment", response_model=AspectSentimentResponse)
def aspect_sentiment(
    live_id: str,
    entities: str | None = Query(None, description="Entities separated by comma"),
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    entity_list = entities.split(",") if entities else None
    result = service.aspect_sentiment(live_id, user_id=user.id, entities=entity_list)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return AspectSentimentResponse(
        live_id=result["live_id"],
        aspects=result["aspects"],
    )


@router.get("/{live_id}/export")
def export_data(
    live_id: str,
    format: str = "json",
    include_analysis: bool = False,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    from app.services.export import ExportService
    exporter = ExportService(service.db, service.sentiment_analyzer, service.topic_extractor)

    messages = list_messages_by_live(service.db, live_id, user_id=user.id)
    if not messages:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")

    safe_name = quote(live_id, safe="")
    if format == "json":
        content = exporter.export_json(live_id, include_analysis=include_analysis, user_id=user.id)
        return Response(content=content, media_type="application/json",
                        headers={"Content-Disposition": f"attachment; filename={safe_name}.json"})
    elif format == "csv":
        content = exporter.export_csv(live_id, user_id=user.id)
        return Response(content=content, media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={safe_name}.csv"})
    elif format == "xlsx":
        try:
            content = exporter.export_xlsx(live_id, user_id=user.id)
        except ImportError as e:
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
        return Response(content=content,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        headers={"Content-Disposition": f"attachment; filename={safe_name}.xlsx"})
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato inválido. Use json, csv ou xlsx.")


@router.get("/{live_id}/topic-sentiment", response_model=TopicSentimentResponse)
def topic_sentiment(
    live_id: str,
    top_n: int = Query(10, ge=1, le=500),
    video_id: str | None = None,
    user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """Cruza tópicos extraídos com sentimento e emoção das mensagens.

    Se video_id for fornecido, enriquece com trechos transcritos do YouTube
    no momento de pico de cada tópico.
    """
    result = service.topic_sentiment(live_id, top_n, user_id=user.id, video_id=video_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return TopicSentimentResponse(
        live_id=result["live_id"],
        topics=[TopicSentimentItem(**t) for t in result["topics"]],
    )
