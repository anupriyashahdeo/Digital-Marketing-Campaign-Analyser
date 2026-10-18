import hashlib
from datetime import UTC, datetime, timedelta

import jwt

from ada.config import settings

ALGO = "HS256"


def _now() -> datetime:
    return datetime.now(UTC)


def _fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def make_session_token(user_id: int, password_hash: str) -> str:
    """Also bound to the password hash, so changing the password signs out every device."""
    exp = _now() + timedelta(minutes=settings.session_minutes)
    return jwt.encode({"sub": str(user_id), "purpose": "session",
                       "fph": _fingerprint(password_hash), "exp": exp},
                      settings.jwt_secret, algorithm=ALGO)


def make_reset_token(user_id: int, password_hash: str) -> str:
    """Bound to the current password hash, so it stops working once used."""
    exp = _now() + timedelta(minutes=settings.reset_minutes)
    return jwt.encode({"sub": str(user_id), "purpose": "reset",
                       "fph": _fingerprint(password_hash), "exp": exp},
                      settings.jwt_secret, algorithm=ALGO)


def decode(token: str, purpose: str) -> dict | None:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
    except jwt.PyJWTError:
        return None
    return data if data.get("purpose") == purpose else None


def token_matches_password(data: dict, password_hash: str) -> bool:
    return data.get("fph") == _fingerprint(password_hash)
