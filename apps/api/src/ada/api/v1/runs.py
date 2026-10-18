from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ada.api.schemas import RunIn, RunOut, RunPage
from ada.db.models import RUN_STATUSES, Membership, Run
from ada.db.session import get_db
from ada.security.deps import require_role, workspace_member

router = APIRouter(prefix="/workspaces/{workspace_id}/runs", tags=["runs"])

# Cost control: each run calls paid APIs, so cap how many can be in flight per workspace.
MAX_ACTIVE_RUNS = 3
ACTIVE = ("queued", "running")
can_edit = require_role("owner", "editor")


def _get_run(db: Session, workspace_id: int, run_id: int) -> Run:
    # Always filter by workspace too: a run id from another workspace must look like "not found".
    run = db.scalar(select(Run).where(Run.id == run_id, Run.workspace_id == workspace_id))
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return run


@router.get("", response_model=RunPage)
def list_runs(m: Membership = Depends(workspace_member), db: Session = Depends(get_db),
              limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
              status_: str | None = Query(None, alias="status")):
    where = [Run.workspace_id == m.workspace_id]
    if status_:
        if status_ not in RUN_STATUSES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown status")
        where.append(Run.status == status_)
    total = db.scalar(select(func.count(Run.id)).where(*where)) or 0
    rows = db.scalars(select(Run).where(*where)
                      .order_by(Run.created_at.desc(), Run.id.desc())
                      .limit(limit).offset(offset)).all()
    return RunPage(items=[RunOut.model_validate(r) for r in rows],
                   total=total, limit=limit, offset=offset)


@router.post("", status_code=201, response_model=RunOut)
def create_run(body: RunIn, m: Membership = Depends(can_edit), db: Session = Depends(get_db)):
    active = db.scalar(select(func.count(Run.id)).where(
        Run.workspace_id == m.workspace_id, Run.status.in_(ACTIVE))) or 0
    if active >= MAX_ACTIVE_RUNS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"You already have {active} analyses in progress. "
                            "Wait for one to finish or cancel it.")
    keywords = body.keywords or [body.category]
    run = Run(workspace_id=m.workspace_id, created_by=m.user_id, category=body.category,
              keywords=keywords, region=body.region, language=body.language)
    db.add(run)
    db.commit()
    db.refresh(run)
    # STEP 3: enqueue the collect task here, e.g. collect_task.delay(run.id)
    return RunOut.model_validate(run)


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: int = Path(ge=1), m: Membership = Depends(workspace_member),
            db: Session = Depends(get_db)):
    return RunOut.model_validate(_get_run(db, m.workspace_id, run_id))


@router.post("/{run_id}/cancel", response_model=RunOut)
def cancel_run(run_id: int = Path(ge=1), m: Membership = Depends(can_edit),
               db: Session = Depends(get_db)):
    run = _get_run(db, m.workspace_id, run_id)
    if run.status not in ACTIVE:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This analysis is already {run.status}")
    run.status = "cancelled"
    run.finished_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    # STEP 3: also revoke the Celery task for this run
    return RunOut.model_validate(run)
