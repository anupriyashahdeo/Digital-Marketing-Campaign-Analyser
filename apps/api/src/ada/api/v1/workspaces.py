from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ada.api.schemas import (
    DashboardOut,
    DashboardStats,
    InterestedVideo,
    RunOut,
    ViewerInterest,
    WorkspaceOut,
)
from ada.config import settings
from ada.db.models import Membership, Run, User, Workspace, YouTubeInsight
from ada.db.session import get_db
from ada.domain.workspaces import ensure_personal_workspace
from ada.security.deps import current_user, workspace_member

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

ACTIVE = ("queued", "running")
EDIT_ROLES = ("owner", "editor")


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(user: User = Depends(current_user), db: Session = Depends(get_db)):
    ensure_personal_workspace(db, user)
    rows = db.execute(select(Workspace, Membership.role)
                      .join(Membership, Membership.workspace_id == Workspace.id)
                      .where(Membership.user_id == user.id)
                      .order_by(Workspace.id)).all()
    return [WorkspaceOut(id=w.id, name=w.name, region=w.region, role=role) for w, role in rows]


def _viewer_interest(db: Session, workspace_id: int) -> ViewerInterest | None:
    latest = db.scalars(select(YouTubeInsight).where(YouTubeInsight.workspace_id == workspace_id)
                        .order_by(YouTubeInsight.analysed_at.desc(), YouTubeInsight.id.desc())
                        .limit(1)).first()
    if not latest or not latest.videos:
        return None
    ranked = sorted(latest.videos, key=lambda v: v["interested_people"], reverse=True)
    return ViewerInterest(
        analysed_at=latest.analysed_at,
        video_count=len(ranked),
        interested_people=sum(v["interested_people"] for v in ranked),
        top_videos=[InterestedVideo(**v) for v in ranked[:5]],
    )


@router.get("/{workspace_id}/dashboard", response_model=DashboardOut)
def dashboard(m: Membership = Depends(workspace_member), db: Session = Depends(get_db)):
    """One call for the whole dashboard screen, so the page loads with a single round trip."""
    ws = db.get(Workspace, m.workspace_id)
    in_ws = Run.workspace_id == ws.id
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0,
                                            tzinfo=None)

    def count(*where) -> int:
        return db.scalar(select(func.count(Run.id)).where(in_ws, *where)) or 0

    stats = DashboardStats(
        total_runs=count(),
        active_runs=count(Run.status.in_(ACTIVE)),
        completed_runs=count(Run.status == "completed"),
        ads_analysed=db.scalar(select(func.coalesce(func.sum(Run.ad_count), 0)).where(in_ws)),
        spent_this_month_usd=round(db.scalar(
            select(func.coalesce(func.sum(Run.spent_usd), 0.0))
            .where(in_ws, Run.created_at >= month_start)), 4),
        run_spend_cap_usd=settings.run_spend_cap_usd,
    )
    recent = db.scalars(select(Run).where(in_ws)
                        .order_by(Run.created_at.desc(), Run.id.desc()).limit(5)).all()
    return DashboardOut(
        workspace=WorkspaceOut(id=ws.id, name=ws.name, region=ws.region, role=m.role),
        stats=stats,
        recent_runs=[RunOut.model_validate(r) for r in recent],
        can_edit=m.role in EDIT_ROLES,
        viewer_interest=_viewer_interest(db, ws.id),
    )
