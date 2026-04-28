from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.services.chat import ChatService
from app.services.sentiment import LeiaSentimentAnalyzer
from app.services.topics import TfidfTopicExtractor

security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    analyzer = LeiaSentimentAnalyzer()
    topic_extractor = TfidfTopicExtractor()
    return ChatService(db, analyzer, topic_extractor)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    from app.models.user import User
    from app.services.auth import verify_token

    user_id = verify_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return user


def get_current_user_optional(
    db: Session = Depends(get_db),
):
    """Retorna o usuário autenticado ou None.
    Usado para compatibilidade com extensão Chrome (que não envia token)."""
    return None
