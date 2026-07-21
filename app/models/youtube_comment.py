from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.infrastructure.database import Base


class YouTubeComment(Base):
    __tablename__ = "youtube_comments"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(20), nullable=False, index=True)
    video_title = Column(String(500), nullable=True)
    author = Column(String(255), nullable=False)
    comment = Column(Text, nullable=False)
    like_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    is_reply = Column(Boolean, default=False)
    reply_level = Column(Integer, default=0)  # 0=Principal, 1=N1, 2=N2, ...
    parent_id = Column(String(100), nullable=True)
    published_at = Column(DateTime, nullable=True)
    collected_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
