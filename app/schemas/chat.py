from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """Payload recebido ao salvar uma nova mensagem."""
    live_id: str = Field(..., json_schema_extra={"example": "live-123"})
    author: str = Field(..., json_schema_extra={"example": "joao_silva"})
    message: str = Field(..., json_schema_extra={"example": "Gostei demais dessa live!"})
    platform: str | None = "youtube"


class MessageResponse(BaseModel):
    """Representação de uma mensagem armazenada."""
    id: int
    live_id: str
    author: str
    message: str
    platform: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class WordFrequencyItem(BaseModel):
    palavra: str
    frequencia: int


class WordFrequencyResponse(BaseModel):
    live_id: str
    word_frequency: list[WordFrequencyItem]


class SentimentResponse(BaseModel):
    live_id: str
    total_messages_analyzed: int
    sentiment_summary: dict[str, int]
    library_used: str
    model: str


class LiveSummary(BaseModel):
    live_id: str
    total_messages: int
    first_message_at: datetime | None = None
    last_message_at: datetime | None = None


class LiveListResponse(BaseModel):
    lives: list[LiveSummary]
    total_lives: int


class TimelineBucket(BaseModel):
    start_time: datetime
    end_time: datetime
    total_messages: int
    sentiments: dict[str, int]


class SentimentTimelineResponse(BaseModel):
    live_id: str
    interval_minutes: int
    timeline: list[TimelineBucket]


class EngagementPeak(BaseModel):
    time: datetime
    message_count: int


class EngagementPeaksResponse(BaseModel):
    live_id: str
    window_minutes: int
    peaks: list[EngagementPeak]


class TopicItem(BaseModel):
    term: str
    score: float


class TopicsResponse(BaseModel):
    live_id: str
    topics: list[TopicItem]


class TopicBucket(BaseModel):
    start_time: datetime
    end_time: datetime
    count: int
    total_messages: int


class TopicTimelineResponse(BaseModel):
    live_id: str
    term: str
    interval_minutes: int
    timeline: list[TopicBucket]