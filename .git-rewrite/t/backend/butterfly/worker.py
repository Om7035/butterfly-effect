"""Celery application and task definitions."""

from celery import Celery
from loguru import logger

from butterfly.config import settings

# Create Celery app
celery_app = Celery(
    "butterfly",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "ingest-fred-every-15-min": {
        "task": "butterfly.ingestion.scheduler.ingest_fred",
        "schedule": 15 * 60,  # 15 minutes
    },
    "ingest-gdelt-every-15-min": {
        "task": "butterfly.ingestion.scheduler.ingest_gdelt",
        "schedule": 15 * 60,  # 15 minutes
    },
}


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    logger.info(f"Debug task called: {self.request.id}")
    return "Debug task completed"
