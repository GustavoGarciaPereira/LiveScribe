from typing import Generator
from fastapi import Depends
from app.infrastructure.database import SessionLocal
from app.services.chat import ChatService

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_chat_service(db=Depends(get_db)) -> ChatService:
    return ChatService(db)