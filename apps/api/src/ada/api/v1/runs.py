from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ada.config import settings
from ada.db.models import Run
from ada.db.session import get_db

router = APIRouter(prefix="/runs", tags=["runs"])


class RunIn(BaseModel):
    category: str
    keywords: list[str] = []
    region: str = settings.region
    language: str = settings.language


@router.post("", status_code=201)
def create_run(body: RunIn, db: Session = Depends(get_db)):
    run = Run(**body.model_dump())
    db.add(run)
    db.commit()
    # TODO: enqueue ingest task here
    return {"id": run.id, "status": run.status}


@router.get("/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    return {"id": run.id, "status": run.status, "spent_usd": run.spent_usd} if run else {}
