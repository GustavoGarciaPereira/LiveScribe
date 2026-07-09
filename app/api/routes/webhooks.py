from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.limiter import limiter
from app.models.user import User
from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate, WebhookResponse

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_webhook(
    request: Request,
    payload: WebhookCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    webhook = Webhook(url=payload.url, event=payload.event, user_id=user.id)
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.get("", response_model=list[WebhookResponse])
def list_webhooks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Webhook).filter(Webhook.user_id == user.id).all()


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.user_id == user.id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook não encontrado")
    db.delete(webhook)
    db.commit()
