from fastapi import APIRouter, Depends, HTTPException, status
from httpx_oauth.clients.google import GoogleOAuth2
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from app.services.auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

google_oauth = GoogleOAuth2(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
)


def _build_response(user: User) -> TokenResponse:
    access_token = create_access_token(user.id)
    return TokenResponse(
        access_token=access_token,
        user=UserInfo(id=user.id, email=user.email, name=user.name, provider=user.provider),
    )


# ── Login local (email/senha) ─────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=User.hash_password(payload.password),
        provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _build_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.password_hash or not user.verify_password(payload.password):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Conta desativada")

    return _build_response(user)


# ── Google OAuth2 ─────────────────────────────────────────────

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
            provider="google",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return _build_response(user)


# ── Perfil ────────────────────────────────────────────────────

@router.get("/me", response_model=UserInfo)
def get_me(user: User = Depends(get_current_user)):
    return UserInfo(id=user.id, email=user.email, name=user.name, provider=user.provider)
