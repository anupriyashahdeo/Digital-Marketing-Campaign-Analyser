from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ada.db.models import User
from ada.db.session import get_db
from ada.security.tokens import decode

COOKIE = "ada_session"


def current_user(token: str | None = Cookie(default=None, alias=COOKIE),
                 db: Session = Depends(get_db)) -> User:
    data = decode(token, "session") if token else None
    user = db.get(User, int(data["sub"])) if data else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user
