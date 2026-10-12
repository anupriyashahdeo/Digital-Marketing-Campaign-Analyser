from celery import Celery

from ada.config import settings

app = Celery("ada", broker=settings.redis_url, backend=settings.redis_url,
             include=["ada.workers.tasks_ai"])
app.conf.update(task_acks_late=True, task_reject_on_worker_lost=True,
                task_default_queue="default", worker_prefetch_multiplier=1)
