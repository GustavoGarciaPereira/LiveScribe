from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.chat import ChatMessage, MessageResponse, WordFrequencyItem, WordFrequencyResponse, SentimentResponse
from app.api.deps import get_chat_service
from app.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/messages", response_model=MessageResponse)
def save_message(payload: ChatMessage, service: ChatService = Depends(get_chat_service)):
    message = service.save_message(payload.live_id, payload.author, payload.message)
    return MessageResponse.model_validate(message)

@router.get("/{live_id}/word-frequency", response_model=WordFrequencyResponse)
def word_frequency(live_id: str, top_n: int = 10, service: ChatService = Depends(get_chat_service)):
    freq_tuples = service.word_frequency(live_id, top_n)
    if not freq_tuples:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    items = [
        WordFrequencyItem(palavra=word, frequencia=count)
        for word, count in freq_tuples
    ]
    return WordFrequencyResponse(live_id=live_id, word_frequency=items)

@router.get("/{live_id}/sentiment", response_model=SentimentResponse)
def sentiment_analysis(live_id: str, service: ChatService = Depends(get_chat_service)):
    summary = service.sentiment_summary(live_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma mensagem encontrada.")
    return SentimentResponse(
        live_id=live_id,
        total_messages_analyzed=summary["total_messages"],
        sentiment_summary=summary["sentiments"],
        library_used="Hugging Face Transformers",
        model=summary["model"],
    )