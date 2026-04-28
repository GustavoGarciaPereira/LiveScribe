from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=500)
    event: str = Field(..., pattern="^(new_message|peak_engagement|sentiment_change)$")


class WebhookResponse(BaseModel):
    id: int
    user_id: int
    url: str
    event: str
    is_active: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
