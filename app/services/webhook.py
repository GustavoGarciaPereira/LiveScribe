import json

import httpx
from sqlalchemy.orm import Session

from app.models.webhook import Webhook


def trigger_webhooks(db: Session, event: str, payload: dict):
    """Dispara POST para todos os webhooks ativos de um evento. Ignora falhas."""
    webhooks = db.query(Webhook).filter(
        Webhook.event == event,
        Webhook.is_active == True,
    ).all()

    if not webhooks:
        return

    body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")

    with httpx.Client(timeout=10) as client:
        for wh in webhooks:
            try:
                client.post(wh.url, content=body, headers={"Content-Type": "application/json"})
            except Exception:
                pass  # ignora falhas silenciosamente
