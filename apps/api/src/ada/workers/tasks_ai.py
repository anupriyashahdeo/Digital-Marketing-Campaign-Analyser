import asyncio

from ada.domain.questions.registry import load
from ada.pipeline.analyse import analyse_ad
from ada.providers.registry import get_decision, get_reviewer
from ada.workers.celery_app import app


@app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5,
          queue="ai")
def analyse_ad_task(self, ad_id: int, text: str):
    """Idempotent: safe to repeat. TODO: persist AnswerRow and CostEntry."""
    answers = asyncio.run(analyse_ad(text, load(), get_decision(), get_reviewer()))
    return [a.model_dump() for a in answers]
