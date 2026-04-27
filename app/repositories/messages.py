from typing import List
from sqlalchemy.orm import Session
from app.models.message import Message

def create_message(db: Session, *, live_id: str, author: str, content: str) -> Message:
    db_message = Message(live_id=live_id, author=author, message=content)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def list_messages_by_live(db: Session, live_id: str) -> List[Message]:
    return (
        db.query(Message)
          .filter(Message.live_id == live_id)
          .order_by(Message.created_at.asc())
          .all()
    )