from fastapi import APIRouter, Depends, Request
from httpx_oauth.clients.google import GoogleOAuth2
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import TokenResponse, UserInfo
from app.services.auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

google_oauth = GoogleOAuth2(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
)


@router.get("/login/google")
async def login_google():
    redirect_uri = "http://localhost:8000/api/auth/callback/google"
    authorization_url = await google_oauth.get_authorization_url(redirect_uri)
    return {"url": authorization_url}


@router.get("/callback/google", response_model=TokenResponse)
async def callback_google(code: str, db: Session = Depends(get_db)):
    redirect_uri = "http://localhost:8000/api/auth/callback/google"
    token = await google_oauth.get_access_token(code, redirect_uri)
    user_info = await google_oauth.get_id_email(token["access_token"])

    user = db.query(User).filter(User.google_id == user_info.id).first()
    if not user:
        user = User(
            email=user_info.email,
            name=user_info.name,
            google_id=user_info.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(user.id)
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserInfo)
def get_me(user: User = Depends(get_current_user)):
    return UserInfo(id=user.id, email=user.email, name=user.name)
