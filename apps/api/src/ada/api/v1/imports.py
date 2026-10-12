from fastapi import APIRouter, UploadFile

from ada.providers.manual.source import parse_csv

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/csv")
async def import_csv(file: UploadFile):
    ads = parse_csv((await file.read()).decode("utf-8"))
    return {"count": len(ads), "video_ids": [a.video_id for a in ads]}
