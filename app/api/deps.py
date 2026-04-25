from fastapi import Depends
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.services.chat import ChatService
from app.services.sentiment import LeiaSentimentAnalyzer


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    analyzer = LeiaSentimentAnalyzer()
    return ChatService(db, analyzer)
