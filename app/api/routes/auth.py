from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from httpx_oauth.clients.google import GoogleOAuth2
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from app.services.auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

google_oauth = GoogleOAuth2(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
)

_COOKIE_MAX_AGE = 24 * 60 * 60  # 24 horas


def _set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )


def _build_response(user: User) -> TokenResponse:
    access_token = create_access_token(user.id)
    return TokenResponse(
        access_token=access_token,
        user=UserInfo(id=user.id, email=user.email, name=user.name, provider=user.provider),
    )


# ── Login local (email/senha) ─────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, response: Response, payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    user = User(
        email=payload.email,
        name=payload.name,
        google_id=f"local_{payload.email}",
        password_hash=User.hash_password(payload.password),
        provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token_response = _build_response(user)
    _set_auth_cookie(response, token_response.access_token)
    return token_response


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, response: Response, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.password_hash or not user.verify_password(payload.password):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Conta desativada")

    token_response = _build_response(user)
    _set_auth_cookie(response, token_response.access_token)
    return token_response


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"detail": "Logout realizado"}


# ── Google OAuth2 ─────────────────────────────────────────────

@router.get("/login/google")
async def login_google():
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    authorization_url = await google_oauth.get_authorization_url(redirect_uri)
    return {"url": authorization_url}


@router.get("/callback/google", response_model=TokenResponse)
async def callback_google(code: str, response: Response, db: Session = Depends(get_db)):
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    token = await google_oauth.get_access_token(code, redirect_uri)
    user_info = await google_oauth.get_id_email(token["access_token"])

    user = db.query(User).filter(User.google_id == user_info.id).first()
    if not user:
        existing = db.query(User).filter(User.email == user_info.email).first()
        if existing:
            existing.google_id = user_info.id
            existing.provider = "google"
            db.commit()
            db.refresh(existing)
            user = existing
        else:
            user = User(
                email=user_info.email,
                name=user_info.name,
                google_id=user_info.id,
                provider="google",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    token_response = _build_response(user)
    _set_auth_cookie(response, token_response.access_token)
    return token_response


# ── Perfil ────────────────────────────────────────────────────

@router.get("/me", response_model=UserInfo)
def get_me(user: User = Depends(get_current_user)):
    return UserInfo(id=user.id, email=user.email, name=user.name, provider=user.provider)
