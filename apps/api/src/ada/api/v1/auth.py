import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ada.config import settings
from ada.db.models import User
from ada.db.session import get_db
from ada.providers.mail.console import ConsoleMailer
from ada.security.deps import COOKIE, current_user
from ada.security.passwords import DUMMY_HASH, hash_password, verify_password
from ada.security.tokens import decode, make_reset_token, make_session_token, reset_token_matches

router = APIRouter(prefix="/auth", tags=["auth"])
mailer = ConsoleMailer()

# Simple per-email throttle. In production, move to Redis (shared across API containers).
_FAILS: dict[str, list[float]] = defaultdict(list)
MAX_FAILS, WINDOW = 5, 15 * 60


def _throttled(email: str) -> bool:
    now = time.time()
    _FAILS[email] = [t for t in _FAILS[email] if now - t < WINDOW]
    return len(_FAILS[email]) >= MAX_FAILS


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str


def _start_session(resp: Response, user: User) -> None:
    resp.set_cookie(COOKIE, make_session_token(user.id), httponly=True, samesite="lax",
                    secure=settings.app_env == "prod", max_age=settings.session_minutes * 60)


@router.post("/signup", status_code=201, response_model=UserOut)
def signup(body: SignupIn, resp: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    _start_session(resp, user)
    return UserOut(id=user.id, email=user.email)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, resp: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    if _throttled(email):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many attempts. Try again in a few minutes.")
    user = db.scalar(select(User).where(User.email == email))
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok:
        _FAILS[email].append(time.time())
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    _FAILS.pop(email, None)
    _start_session(resp, user)
    return UserOut(id=user.id, email=user.email)


@router.post("/logout", status_code=204)
def logout(resp: Response):
    resp.delete_cookie(COOKIE)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return UserOut(id=user.id, email=user.email)


@router.post("/forgot-password")
def forgot_password(body: ForgotIn, db: Session = Depends(get_db)):
    """Always returns the same message so the endpoint can't be used to discover accounts."""
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user:
        token = make_reset_token(user.id, user.password_hash)
        link = f"{settings.frontend_url}/reset-password?token={token}"
        mailer.send(user.email, "Reset your Ad Campaign Analyser password",
                    f"Use this link within {settings.reset_minutes} minutes: {link}")
    return {"message": "If an account exists for that email, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(body: ResetIn, db: Session = Depends(get_db)):
    data = decode(body.token, "reset")
    user = db.get(User, int(data["sub"])) if data else None
    if not user or not reset_token_matches(data, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired")
    user.password_hash = hash_password(body.password)
    db.commit()
    return {"message": "Password updated. You can now sign in."}
