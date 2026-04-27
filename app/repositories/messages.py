from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.message import Message

def create_message(db: Session, *, live_id: str, author: str, content: str, platform: str = "youtube") -> Message:
    db_message = Message(live_id=live_id, author=author, message=content, platform=platform)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def list_messages_by_live(db: Session, live_id: str) -> list[Message]:
    return (
        db.query(Message)
          .filter(Message.live_id == live_id)
          .order_by(Message.created_at.asc())
          .all()
    )

def list_lives(db: Session) -> list[dict]:
    """Retorna lives agrupadas com contagem e timestamps."""
    rows = (
        db.query(
            Message.live_id,
            func.count(Message.id).label("total_messages"),
            func.min(Message.created_at).label("first_message_at"),
            func.max(Message.created_at).label("last_message_at"),
        )
        .group_by(Message.live_id)
        .order_by(func.max(Message.created_at).desc())
        .all()
    )
    return [
        {
            "live_id": row.live_id,
            "total_messages": row.total_messages,
            "first_message_at": row.first_message_at,
            "last_message_at": row.last_message_at,
        }
        for row in rows
    ]