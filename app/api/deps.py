from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal
from app.services.chat import ChatService
from app.services.report_queue import ReportQueue
from app.services.sentiment import LeiaSentimentAnalyzer
from app.services.topics import TfidfTopicExtractor
from app.services.emojis import RegexEmojiExtractor
from app.services.modality import LexiconModalityAnalyzer
from app.services.emotion import LexiconEmotionAnalyzer
from app.services.framing import LexiconFramingAnalyzer
from app.services.sarcasm import LexiconSarcasmAnalyzer
from app.services.aspects import LexiconAspectAnalyzer

optional_security = HTTPBearer(auto_error=False)

# ── Fila de relatórios (singleton) ────────────────────────────

_report_queue: ReportQueue | None = None


def get_report_queue() -> ReportQueue:
    """Retorna a fila de relatórios compartilhada."""
    if _report_queue is None:
        raise RuntimeError("ReportQueue não foi inicializada.")
    return _report_queue


def init_report_queue() -> ReportQueue:
    """Inicializa e retorna a fila de relatórios (chamado no lifespan)."""
    global _report_queue
    if _report_queue is None:
        _report_queue = ReportQueue()
    return _report_queue


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@lru_cache(maxsize=1)
def get_analyzers():
    """Retorna os analisadores NLP cacheados — instanciados uma única vez."""
    return {
        "sentiment": LeiaSentimentAnalyzer(),
        "topic": TfidfTopicExtractor(),
        "emoji": RegexEmojiExtractor(),
        "modality": LexiconModalityAnalyzer(),
        "emotion": LexiconEmotionAnalyzer(),
        "framing": LexiconFramingAnalyzer(),
        "sarcasm": LexiconSarcasmAnalyzer(),
        "aspect": LexiconAspectAnalyzer(),
    }


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    analyzers = get_analyzers()
    return ChatService(
        db,
        analyzers["sentiment"],
        analyzers["topic"],
        analyzers["emoji"],
        analyzers["modality"],
        analyzers["emotion"],
        analyzers["framing"],
        analyzers["sarcasm"],
        analyzers["aspect"],
    )


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
):
    """Autentica via Bearer header (extensão) ou HttpOnly cookie (dashboard)."""
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")

    from app.models.user import User
    from app.services.auth import verify_token

    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return user
