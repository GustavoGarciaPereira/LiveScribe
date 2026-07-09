import json
import logging

import httpx

from app.infrastructure.database import SessionLocal
from app.models.webhook import Webhook

logger = logging.getLogger(__name__)


async def trigger_webhooks(event: str, payload: dict, user_id: int | None = None):
    """Dispara POST para webhooks ativos de um evento (assíncrono, em background).
    
    Se user_id for fornecido, dispara apenas webhooks do usuário dono do recurso.
    Cria sua própria sessão de banco para ser segura em BackgroundTasks.
    Falhas são logadas mas nunca propagadas — o request principal não é afetado.
    """
    db = SessionLocal()
    try:
        query = db.query(Webhook).filter(
            Webhook.event == event,
            Webhook.is_active == True,
        )
        if user_id is not None:
            query = query.filter(Webhook.user_id == user_id)
        webhooks = query.all()

        if not webhooks:
            return

        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")

        async with httpx.AsyncClient(timeout=10) as client:
            for wh in webhooks:
                try:
                    await client.post(wh.url, content=body, headers={"Content-Type": "application/json"})
                except Exception as e:
                    logger.error(f"Webhook {wh.url} (event={event}) falhou: {e}")
    finally:
        db.close()
