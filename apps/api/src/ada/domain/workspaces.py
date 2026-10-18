"""Workspace setup. Every user always has at least one workspace they own."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ada.config import settings
from ada.db.models import Membership, User, Workspace


def create_personal_workspace(db: Session, user: User) -> Workspace:
    """Adds (does not commit) a workspace owned by `user`. Call inside the signup transaction."""
    local = user.email.split("@", 1)[0][:60]
    ws = Workspace(name=f"{local}'s workspace", region=settings.region)
    db.add(ws)
    db.flush()   # assigns ws.id
    db.add(Membership(user_id=user.id, workspace_id=ws.id, role="owner"))
    return ws


def ensure_personal_workspace(db: Session, user: User) -> None:
    """Backfill for accounts created before workspaces existed. Safe to call repeatedly."""
    if not db.scalar(select(Membership.id).where(Membership.user_id == user.id).limit(1)):
        create_personal_workspace(db, user)
        db.commit()
