"""Task queue: the browser hands in a CSV, a model running on another machine picks it up.

Browser (signed in, workspace member):
  POST /workspaces/{id}/taskinput            upload the CSV -> {task_id}
  GET  /workspaces/{id}/taskinput/{task_id}  status, and the output once done (creator only)

Model worker (Authorization: Bearer $TASK_WORKER_KEY), polling every ~10 s:
  GET  /taskoutput                           claim the oldest unfinished task -> 200, or 204
  POST /taskoutput/{task_id}                 send the output (or an error) with the lease token

Claims are atomic (row lock + compare-and-set), so two workers never get the same task. A worker
that dies mid-task loses its lease after TASK_LEASE_SECONDS and the task is handed out again,
up to TASK_MAX_ATTEMPTS times. Tasks nobody finishes in TASK_EXPIRE_MINUTES are marked failed so
the browser stops waiting.
"""
import hmac
import logging
import re
import secrets
import uuid
from datetime import timedelta

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Path,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from ada.api.schemas.tasks import TaskClaimOut, TaskCreatedOut, TaskOut, TaskResultIn
from ada.api.v1.workspaces import EDIT_ROLES
from ada.api.v1.youtube import MAX_CSV_BYTES, save_interest
from ada.config import settings
from ada.db.models import AnalysisTask, Membership, utcnow
from ada.db.session import get_db
from ada.pipeline.youtube_insights import read_csv
from ada.security.deps import workspace_member

log = logging.getLogger("ada.tasks")

MAX_VIDEOS = 500
MAX_RESULT_BYTES = 5_000_000
POLL_AFTER_SECONDS = 3
_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
_TASK_ID = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
EXPIRED = "The analysis took too long (the model may be offline). Please try again."
GAVE_UP = "The model couldn't finish this analysis. Please try again later."

user_router = APIRouter(prefix="/workspaces/{workspace_id}/taskinput", tags=["tasks"])
worker_router = APIRouter(prefix="/taskoutput", tags=["tasks (worker)"])


# --------------------------------------------------------------------------- helpers
def _status(t: AnalysisTask) -> str:
    if t.task_complete:
        return "failed" if t.error else "done"
    return "processing" if t.claimed_at else "queued"


def _finish(t: AnalysisTask, *, output: dict | None = None, error: str | None = None) -> None:
    t.task_complete = 1
    t.task_output, t.error = output, error
    t.completed_at = utcnow()
    t.task_input = None          # don't keep uploaded comments once they're processed
    t.lease_token = None


def _expire_if_stale(db: Session, t: AnalysisTask) -> None:
    if not t.task_complete and utcnow() - t.created_at > timedelta(minutes=settings.task_expire_minutes):
        _finish(t, error=EXPIRED)
        db.commit()


def _validate_csv(content: bytes) -> str:
    """Reject anything the worker couldn't process, now, instead of after a wait in the queue."""
    if not content.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The CSV is empty.")
    try:
        text = content.decode("utf-8-sig")
        videos = read_csv(text)
    except UnicodeDecodeError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "The CSV must be UTF-8 text.") from e
    except (ValueError, KeyError) as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Couldn't read that CSV: {e}") from e
    if "\x00" in text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The CSV contains binary data.")
    if not videos:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The CSV has no videos.")
    if len(videos) > MAX_VIDEOS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"The CSV has {len(videos)} videos; the limit is {MAX_VIDEOS}.")
    bad = next((v["video_id"] for v in videos if not _VIDEO_ID.fullmatch(v["video_id"])), None)
    if bad is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"'{bad[:20]}' isn't a YouTube video id.")
    return text


async def _read_limited(request: Request, limit: int) -> bytes:
    """Read the body but stop at `limit`, whatever Content-Length claims."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Result too large.")
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Result too large.")
    return bytes(body)


def worker_auth(authorization: str | None = Header(default=None)) -> None:
    """Bearer TASK_WORKER_KEY, compared in constant time. Queue off (503) when no key is set."""
    key = settings.task_worker_key
    if not key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Task queue is not configured.")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(token.strip().encode(), key.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid worker key",
                            headers={"WWW-Authenticate": "Bearer"})


# --------------------------------------------------------------------------- browser
@user_router.post("", response_model=TaskCreatedOut, status_code=status.HTTP_202_ACCEPTED)
async def task_input(file: UploadFile, m: Membership = Depends(workspace_member),
                     db: Session = Depends(get_db)):
    """Queue a YouTube 'Download CSV' export for the model. Returns at once with a task id."""
    content = await file.read(MAX_CSV_BYTES + 1)
    if len(content) > MAX_CSV_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "CSV is over 2 MB.")
    text = _validate_csv(content)
    pending = db.scalar(select(func.count()).select_from(AnalysisTask).where(
        AnalysisTask.created_by == m.user_id, AnalysisTask.task_complete == 0,
        AnalysisTask.created_at > utcnow() - timedelta(minutes=settings.task_expire_minutes)))
    if pending >= settings.task_max_pending_per_user:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "You already have analyses running. Wait for one to finish.")
    t = AnalysisTask(id=str(uuid.uuid4()), workspace_id=m.workspace_id, created_by=m.user_id,
                     task_input=text, task_complete=0, attempts=0,
                     save_to_dashboard=m.role in EDIT_ROLES, created_at=utcnow())
    db.add(t)
    db.commit()
    log.info("task %s queued by user %s (workspace %s, %d bytes)",
             t.id, m.user_id, m.workspace_id, len(content))
    return TaskCreatedOut(task_id=t.id, status="queued", poll_after_seconds=POLL_AFTER_SECONDS)


@user_router.get("/{task_id}", response_model=TaskOut)
def task_status(task_id: str = Path(pattern=_TASK_ID), m: Membership = Depends(workspace_member),
                db: Session = Depends(get_db)):
    """Only the person who queued it can read it; anyone else gets 404, like a missing id."""
    t = db.get(AnalysisTask, task_id)
    if not t or t.workspace_id != m.workspace_id or t.created_by != m.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    _expire_if_stale(db, t)
    return TaskOut(task_id=t.id, status=_status(t), task_complete=t.task_complete,
                   created_at=t.created_at, completed_at=t.completed_at, error=t.error,
                   output=t.task_output)


# --------------------------------------------------------------------------- worker
@worker_router.get("", response_model=TaskClaimOut, dependencies=[Depends(worker_auth)],
                   responses={204: {"description": "Nothing to do"}})
def claim_task(db: Session = Depends(get_db)):
    """Hand the oldest unfinished task (never claimed, or whose lease ran out) to the caller."""
    now = utcnow()
    lease_cutoff = now - timedelta(seconds=settings.task_lease_seconds)
    expire_cutoff = now - timedelta(minutes=settings.task_expire_minutes)
    for _ in range(5):                  # another worker may win the race; try the next one
        t = db.scalar(
            select(AnalysisTask)
            .where(AnalysisTask.task_complete == 0,
                   or_(AnalysisTask.claimed_at.is_(None), AnalysisTask.claimed_at < lease_cutoff))
            .order_by(AnalysisTask.created_at).limit(1)
            .with_for_update(skip_locked=True))          # Postgres; SQLite ignores it
        if t is None:
            _purge_old(db)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        if t.created_at < expire_cutoff or t.attempts >= settings.task_max_attempts:
            _finish(t, error=EXPIRED if t.created_at < expire_cutoff else GAVE_UP)
            db.commit()
            log.warning("task %s given up after %d attempts", t.id, t.attempts)
            continue
        token = secrets.token_urlsafe(32)
        won = db.execute(
            update(AnalysisTask)
            .where(AnalysisTask.id == t.id, AnalysisTask.task_complete == 0,
                   AnalysisTask.attempts == t.attempts)              # compare-and-set
            .values(claimed_at=now, lease_token=token, attempts=t.attempts + 1)
            .execution_options(synchronize_session=False)).rowcount
        db.commit()
        if won != 1:
            continue
        log.info("task %s claimed (attempt %d)", t.id, t.attempts + 1)
        return TaskClaimOut(task_id=t.id, kind=t.kind, lease_token=token,
                            lease_seconds=settings.task_lease_seconds, attempt=t.attempts + 1,
                            task_input=t.task_input or "")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@worker_router.post("/{task_id}", status_code=status.HTTP_204_NO_CONTENT,
                    dependencies=[Depends(worker_auth)])
async def submit_output(request: Request, task_id: str = Path(pattern=_TASK_ID),
                        db: Session = Depends(get_db)):
    """Store the model's output (task_complete -> 1). Needs the lease token from the claim, so a
    worker whose lease ran out can't overwrite the result of the one that took over."""
    raw = await _read_limited(request, MAX_RESULT_BYTES)
    try:
        body = TaskResultIn.model_validate_json(raw)
    except ValidationError as e:
        log.warning("task %s: rejected worker output (%d errors)", task_id, e.error_count())
        detail = [{"loc": list(err["loc"]), "msg": err["msg"]} for err in e.errors()[:20]]
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail) from e
    t = db.get(AnalysisTask, task_id)
    if (not t or t.task_complete or not t.lease_token
            or not hmac.compare_digest(t.lease_token.encode(), body.lease_token.encode())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Task is not claimed with this lease.")
    if body.error is not None:
        if body.retry and t.attempts < settings.task_max_attempts:
            t.claimed_at, t.lease_token = None, None          # back in the queue
            log.warning("task %s: worker error, will retry: %s", t.id, body.error)
        else:
            _finish(t, error=body.error)
            log.warning("task %s failed: %s", t.id, body.error)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    output = body.output.model_dump(mode="json")
    _finish(t, output=output)
    if t.save_to_dashboard and output["videos"]:
        save_interest(db, t.workspace_id, output["videos"])       # commits
    else:
        db.commit()
    log.info("task %s done (%d videos)", t.id, len(output["videos"]))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _purge_old(db: Session) -> None:
    """Finished tasks only live a few days. Runs when the queue is empty, so it's cheap."""
    cutoff = utcnow() - timedelta(days=settings.task_keep_days)
    db.execute(delete(AnalysisTask).where(AnalysisTask.task_complete == 1,
                                          AnalysisTask.completed_at < cutoff))
    db.commit()
