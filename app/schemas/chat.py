from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """Payload recebido ao salvar uma nova mensagem."""
    live_id: str = Field(..., example="live-123")
    author: str = Field(..., example="joao_silva")
    message: str = Field(..., example="Gostei demais dessa live!")


class MessageResponse(BaseModel):
    """Representação de uma mensagem armazenada."""
    id: int
    live_id: str
    author: str
    message: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class WordFrequencyItem(BaseModel):
    palavra: str
    frequencia: int


class WordFrequencyResponse(BaseModel):
    live_id: str
    word_frequency: List[WordFrequencyItem]


class SentimentResponse(BaseModel):
    live_id: str
    total_messages_analyzed: int
    sentiment_summary: Dict[str, int]
    library_used: str
    model: str