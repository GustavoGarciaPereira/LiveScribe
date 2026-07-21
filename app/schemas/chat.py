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


class SentimentStatistics(BaseModel):
    mean: float | None = None
    std_dev: float | None = None
    ci_95: list[float] | None = None


class SentimentResponse(BaseModel):
    live_id: str
    total_messages_analyzed: int
    sentiment_summary: dict[str, int]
    statistics: SentimentStatistics | None = None
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
    statistics: SentimentStatistics | None = None
    significant_change: bool = False
    p_value: float | None = None
    change_direction: str | None = "none"
    change_magnitude: float | None = None


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
class EmojiItem(BaseModel):
    emoji: str
    count: int
    sentiment: str


class EmojiResponse(BaseModel):
    live_id: str
    total_emojis: int
    emojis: list[EmojiItem]


class AuthorItem(BaseModel):
    author: str
    messages: int
    first_message_at: datetime | None = None
    last_message_at: datetime | None = None
    avg_sentiment: str | None = None


class TopAuthorsResponse(BaseModel):
    live_id: str
    total_authors: int
    authors: list[AuthorItem]


class QuestionItem(BaseModel):
    text: str
    count: int
    examples: list[str]


class QuestionsResponse(BaseModel):
    live_id: str
    questions: list[QuestionItem]


class ModalityBucket(BaseModel):
    start_time: datetime
    end_time: datetime
    total_messages: int
    certeza: int
    duvida: int
    enfase: int


class ModalityTimelineResponse(BaseModel):
    live_id: str
    interval_minutes: int
    timeline: list[ModalityBucket]


class EmotionBucket(BaseModel):
    start_time: datetime
    end_time: datetime
    total_messages: int
    alegria: int
    raiva: int
    medo: int
    surpresa: int
    tristeza: int
    nojo: int


class EmotionTimelineResponse(BaseModel):
    live_id: str
    interval_minutes: int
    timeline: list[EmotionBucket]


class TopicSentimentItem(BaseModel):
    topic: str
    message_count: int
    sentiment: dict[str, int]
    statistics: SentimentStatistics | None = None
    dominant_emotion: str
    peak_minute: str | None = None
    transcript_snippet: str | None = None
    peak_timestamp: float | None = None


class TopicSentimentResponse(BaseModel):
    live_id: str
    topics: list[TopicSentimentItem]


class FramingResponse(BaseModel):
    live_id: str
    total_messages: int
    framing: dict[str, int]


class SarcasmResponse(BaseModel):
    live_id: str
    total_messages: int
    sarcasm: dict[str, int]


class AspectSentimentItem(BaseModel):
    messages: int
    sentiment: dict[str, int]


class AspectSentimentResponse(BaseModel):
    live_id: str
    aspects: dict[str, AspectSentimentItem]


# ── YouTube Comments ───────────────────────────────────────────

class YouTubeCommentResponse(BaseModel):
    id: int
    video_id: str
    video_title: str | None = None
    author: str
    comment: str
    like_count: int = 0
    reply_count: int = 0
    is_reply: bool = False
    reply_level: int = 0
    parent_id: str | None = None
    published_at: str | None = None
    collected_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class YouTubeVideoSummary(BaseModel):
    video_id: str
    video_title: str | None = None
    total_comments: int
    collected_at: str | None = None


class YouTubeVideoListResponse(BaseModel):
    videos: list[YouTubeVideoSummary]


class YouTubeFetchResponse(BaseModel):
    video_id: str
    video_title: str | None = None
    total_comments: int
    total_replies: int
    total_items: int
    max_depth: int = -1
