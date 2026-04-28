from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import User
from app.schemas.chat import (
    ChatMessage, MessageResponse, WordFrequencyItem, WordFrequencyResponse,
    SentimentResponse, LiveSummary, LiveListResponse,
    SentimentTimelineResponse, TimelineBucket,
    EngagementPeaksResponse, EngagementPeak,
    TopicsResponse, TopicItem,
)
from app.api.deps import get_chat_service, get_current_user_optional
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/messages", response_model=MessageResponse)
def save_message(
    payload: ChatMessage,
    user: Optional[User] = Depends(get_current_user_optional),
    service: ChatService = Depends(get_chat_service),
):
    message = service.save_message(
        payload.live_id, payload.author, payload.message,
        payload.platform or "youtube",
        user_id=user.id if user else None,
    )
    return MessageResponse.model_validate(message)

@router.get("/lives", response_model=LiveListResponse)
def list_lives_endpoint(
    user: Optional[User] = Depends(get_current_user_optional),
    service: ChatService = Depends(get_chat_service),
):
    lives = service.list_lives()
    return LiveListResponse(
        lives=[LiveSummary(**live) for live in lives],
        total_lives=len(lives),
    )


@router.get("/{live_id}/word-frequency", response_model=WordFrequencyResponse)
def word_frequency(
    live_id: str,
    top_n: int = 10,
    user: Optional[User] = Depends(get_current_user_optional),
    service: ChatService = Depends(get_chat_service),
):
    freq_tuples = service.word_frequency(live_id, top_n)
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
    user: Optional[User] = Depends(get_current_user_optional),
    service: ChatService = Depends(get_chat_service),
):
    try:
        summary = service.sentiment_summary(live_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return SentimentResponse(
        live_id=live_id,
        total_messages_analyzed=summary["total_messages"],
        sentiment_summary=summary["sentiments"],
        library_used="Hugging Face Transformers",
        model=summary["model"],
    )


@router.get("/{live_id}/sentiment-timeline", response_model=SentimentTimelineResponse)
def sentiment_timeline(
    live_id: str,
    interval_minutes: int = 5,
    user: Optional[User] = Depends(get_current_user_optional),
    service: ChatService = Depends(get_chat_service),
):
    result = service.sentiment_timeline(live_id, interval_minutes)
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
    top_n: int = 5,
    window_minutes: int = 1,
    user: Optional[User] = Depends(get_current_user_optional),
    service: ChatService = Depends(get_chat_service),
):
    result = service.engagement_peaks(live_id, top_n, window_minutes)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return EngagementPeaksResponse(
        live_id=result["live_id"],
        window_minutes=result["window_minutes"],
        peaks=[EngagementPeak(**peak) for peak in result["peaks"]],
    )


@router.get("/{live_id}/topics", response_model=TopicsResponse)
def topics(
    live_id: str,
    top_n: int = 10,
    user: Optional[User] = Depends(get_current_user_optional),
    service: ChatService = Depends(get_chat_service),
):
    result = service.extract_topics(live_id, top_n)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return TopicsResponse(
        live_id=result["live_id"],
        topics=[TopicItem(**t) for t in result["topics"]],
    )
