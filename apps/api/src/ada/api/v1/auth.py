import time
from collections import defaultdict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ada.config import settings
from ada.db.models import User
from ada.db.session import get_db
from ada.domain.workspaces import create_personal_workspace
from ada.providers.registry import get_mailer
from ada.security.deps import COOKIE, current_user
from ada.security.passwords import DUMMY_HASH, hash_password, verify_password
from ada.security.tokens import decode, make_reset_token, make_session_token, token_matches_password

router = APIRouter(prefix="/auth", tags=["auth"])
mailer = get_mailer()

# Simple in-memory throttles. In production, move to Redis (shared across API containers).
_FAILS: dict[str, list[float]] = defaultdict(list)          # failed logins, per email
_RESET_MAILS: dict[str, list[float]] = defaultdict(list)    # reset emails sent, per email
_RESET_IPS: dict[str, list[float]] = defaultdict(list)      # reset requests, per client IP
MAX_FAILS, MAX_RESET_MAILS, MAX_RESET_IPS, WINDOW = 5, 3, 20, 15 * 60


def _throttled(bucket: dict[str, list[float]], key: str, limit: int) -> bool:
    now = time.time()
    bucket[key] = [t for t in bucket[key] if now - t < WINDOW]
    return len(bucket[key]) >= limit


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(max_length=1024)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str


def _start_session(resp: Response, user: User) -> None:
    resp.set_cookie(COOKIE, make_session_token(user.id, user.password_hash), httponly=True, samesite="lax",
                    secure=settings.app_env == "prod", max_age=settings.session_minutes * 60)


@router.post("/signup", status_code=201, response_model=UserOut)
def signup(body: SignupIn, resp: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()                               # assigns user.id
    create_personal_workspace(db, user)      # same transaction: no user is left without one
    db.commit()
    _start_session(resp, user)
    return UserOut(id=user.id, email=user.email)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, resp: Response, db: Session = Depends(get_db)):
    email = body.email.lower()
    if _throttled(_FAILS, email, MAX_FAILS):
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
def forgot_password(body: ForgotIn, request: Request, tasks: BackgroundTasks,
                    db: Session = Depends(get_db)):
    """Always returns the same message so the endpoint can't be used to discover accounts.
    Mail is sent after the response so its timing doesn't reveal whether the account exists."""
    ip = request.client.host if request.client else "unknown"
    if _throttled(_RESET_IPS, ip, MAX_RESET_IPS):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many requests. Try again in a few minutes.")
    _RESET_IPS[ip].append(time.time())
    email = body.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    # Per-email cap stops inbox flooding; it fails silently so it can't reveal the account.
    if user and not _throttled(_RESET_MAILS, email, MAX_RESET_MAILS):
        _RESET_MAILS[email].append(time.time())
        token = make_reset_token(user.id, user.password_hash)
        link = f"{settings.frontend_url}/reset-password?token={token}"
        tasks.add_task(mailer.send, user.email, "Reset your Ad Campaign Analyser password",
                       f"Use this link within {settings.reset_minutes} minutes: {link}")
    return {"message": "If an account exists for that email, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(body: ResetIn, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    data = decode(body.token, "reset")
    user = db.get(User, int(data["sub"])) if data else None
    if not user or not token_matches_password(data, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired")
    # A new hash makes this link and every existing session invalid (both carry the old fingerprint)
    user.password_hash = hash_password(body.password)
    db.commit()
    _FAILS.pop(user.email, None)
    _RESET_MAILS.pop(user.email, None)
    tasks.add_task(mailer.send, user.email, "Your Ad Campaign Analyser password was changed",
                   "Your password was just reset and you were signed out on all devices. "
                   "If this wasn't you, reset your password again right away.")
    return {"message": "Password updated. You can now sign in."}
