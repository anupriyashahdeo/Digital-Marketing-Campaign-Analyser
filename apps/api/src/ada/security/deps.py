from collections.abc import Callable

from fastapi import Cookie, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ada.db.models import Membership, User
from ada.db.session import get_db
from ada.security.tokens import decode, token_matches_password

COOKIE = "ada_session"


def current_user(token: str | None = Cookie(default=None, alias=COOKIE),
                 db: Session = Depends(get_db)) -> User:
    data = decode(token, "session") if token else None
    user = db.get(User, int(data["sub"])) if data else None
    if not user or not token_matches_password(data, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


def workspace_member(workspace_id: int = Path(ge=1), user: User = Depends(current_user),
                     db: Session = Depends(get_db)) -> Membership:
    """Every /workspaces/{workspace_id}/... route goes through this.
    Non-members get 404, not 403, so workspace ids can't be probed."""
    m = db.scalar(select(Membership).where(Membership.workspace_id == workspace_id,
                                           Membership.user_id == user.id))
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    return m


def require_role(*roles: str) -> Callable[..., Membership]:
    """Use as Depends(require_role("owner", "editor")) on routes that change data."""
    def check(m: Membership = Depends(workspace_member)) -> Membership:
        if m.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                "Your role in this workspace can't do that")
        return m
    return check
