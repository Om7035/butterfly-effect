"""Celery application and task definitions."""

import os
from celery import Celery
from loguru import logger

from butterfly.config import settings
from butterfly.logging_utils import log_stage, DebugTimer

# Use fakeredis as broker/backend when real Redis isn't available
def _get_broker_url() -> str:
    """Return broker URL — falls back to in-memory if Redis unavailable."""
    try:
        import redis
        r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        return settings.redis_url
    except Exception:
        logger.warning("[WORKER] Redis unavailable — using in-memory broker (tasks won't persist)")
        return "memory://"

_broker = _get_broker_url()
_backend = settings.celery_result_backend if _broker != "memory://" else "cache+memory://"

logger.info(f"⚙️  Celery broker: {_broker}")
logger.info(f"⚙️  Celery backend: {_backend}")

celery_app = Celery("butterfly", broker=_broker, backend=_backend)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
)

celery_app.conf.beat_schedule = {
    "ingest-fred-every-15-min": {
        "task": "butterfly.ingestion.scheduler.ingest_fred",
        "schedule": 15 * 60,
    },
    "ingest-gdelt-every-15-min": {
        "task": "butterfly.ingestion.scheduler.ingest_gdelt",
        "schedule": 15 * 60,
    },
}


@celery_app.task(bind=True)
def debug_task(self):
    logger.info(f"🧪 Debug task called: {self.request.id}")
    log_stage("DEBUG_TASK", "start")
    try:
        logger.info("✅ Debug task completed successfully")
        log_stage("DEBUG_TASK", "done")
        return "Debug task completed"
    except Exception as e:
        logger.error(f"❌ Debug task failed: {e}")
        log_stage("DEBUG_TASK", "error", {"error": str(e)})
        raise
