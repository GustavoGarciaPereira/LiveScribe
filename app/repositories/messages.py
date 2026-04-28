from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.models.message import Message

def create_message(db: Session, *, live_id: str, author: str, content: str, platform: str = "youtube", user_id: int | None = None) -> Message:
    db_message = Message(live_id=live_id, author=author, message=content, platform=platform, user_id=user_id)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def list_messages_by_live(db: Session, live_id: str, user_id: int | None = None) -> list[Message]:
    q = db.query(Message).filter(Message.live_id == live_id)
    if user_id is not None:
        q = q.filter(or_(Message.user_id == user_id, Message.user_id.is_(None)))
    return q.order_by(Message.created_at.asc()).all()

def list_lives(db: Session, user_id: int | None = None) -> list[dict]:
    """Retorna lives agrupadas com contagem e timestamps. Opcionalmente filtra por user_id."""
    q = db.query(
        Message.live_id,
        func.count(Message.id).label("total_messages"),
        func.min(Message.created_at).label("first_message_at"),
        func.max(Message.created_at).label("last_message_at"),
    )
    if user_id is not None:
        q = q.filter(or_(Message.user_id == user_id, Message.user_id.is_(None)))
    rows = (
        q.group_by(Message.live_id)
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