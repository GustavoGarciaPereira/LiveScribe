from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.core.timezone import now as now_local
from app.infrastructure.database import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_live_user", "live_id", "user_id"),
        Index("ix_messages_live_created", "live_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    live_id = Column(String(255), index=True, nullable=False)
    author = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    platform = Column(String(50), nullable=False, default="youtube")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=now_local,
    )