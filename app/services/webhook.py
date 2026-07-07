import json
import logging

import httpx

from app.infrastructure.database import SessionLocal
from app.models.webhook import Webhook

logger = logging.getLogger(__name__)


async def trigger_webhooks(event: str, payload: dict):
    """Dispara POST para todos os webhooks ativos de um evento (assíncrono, em background).
    
    Cria sua própria sessão de banco para ser seguro em BackgroundTasks.
    Falhas são logadas mas nunca propagadas — o request principal não é afetado.
    """
    db = SessionLocal()
    try:
        webhooks = db.query(Webhook).filter(
            Webhook.event == event,
            Webhook.is_active == True,
        ).all()

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
