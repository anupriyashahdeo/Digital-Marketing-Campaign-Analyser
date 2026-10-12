import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/runs", tags=["events"])


@router.get("/{run_id}/events")
async def stream(run_id: int):
    async def gen():
        for step in ["collect", "to_text", "analyse", "escalate", "score", "summarise"]:
            yield f"data: {json.dumps({'run_id': run_id, 'step': step})}\n\n"
            await asyncio.sleep(0.2)   # TODO: subscribe to Redis pub/sub for real progress
    return StreamingResponse(gen(), media_type="text/event-stream")
