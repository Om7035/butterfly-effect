"""Celery task scheduler for data ingestion."""

import uuid

from loguru import logger
from sqlalchemy import select

from butterfly.db.postgres import AsyncSessionLocal
from butterfly.ingestion.fred import FREDIngester
from butterfly.ingestion.gdelt import GDELTIngester
from butterfly.models.event import EventORM
from butterfly.worker import celery_app


async def save_events(events_data: list) -> int:
    """Save events to PostgreSQL.

    Args:
        events_data: List of event dictionaries

    Returns:
        Number of events saved
    """
    if not events_data:
        return 0

    async with AsyncSessionLocal() as session:
        try:
            count = 0
            for event_data in events_data:
                # Check if event already exists
                stmt = select(EventORM).where(
                    EventORM.title == event_data.get("title"),
                    EventORM.source == event_data.get("source"),
                    EventORM.occurred_at == event_data.get("occurred_at"),
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if not existing:
                    # Create new event
                    event_orm = EventORM(
                        event_id=f"event_{uuid.uuid4().hex[:12]}",
                        title=event_data.get("title"),
                        description=event_data.get("description"),
                        source=event_data.get("source"),
                        source_url=event_data.get("source_url"),
                        occurred_at=event_data.get("occurred_at"),
                        raw_text=event_data.get("raw_text"),
                        entities=[],
                        processed=False,
                    )
                    session.add(event_orm)
                    count += 1

            await session.commit()
            return count
        except Exception as e:
            logger.error(f"Failed to save events: {e}")
            await session.rollback()
            return 0


@celery_app.task(bind=True)
def ingest_fred(self):
    """Celery task to ingest FRED data."""
    import asyncio

    try:
        logger.info("Starting FRED ingestion task")
        ingester = FREDIngester()
        events = asyncio.run(ingester.ingest())

        # Convert EventCreate to dict for storage
        events_data = [event.model_dump() for event in events]
        saved = asyncio.run(save_events(events_data))

        logger.info(f"FRED ingestion task complete: {saved} events saved")
        return {"status": "success", "events_saved": saved}
    except Exception as e:
        logger.error(f"FRED ingestion task failed: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(bind=True)
def ingest_gdelt(self):
    """Celery task to ingest GDELT data."""
    import asyncio

    try:
        logger.info("Starting GDELT ingestion task")
        ingester = GDELTIngester()
        events = asyncio.run(ingester.ingest())

        # Convert EventCreate to dict for storage
        events_data = [event.model_dump() for event in events]
        saved = asyncio.run(save_events(events_data))

        logger.info(f"GDELT ingestion task complete: {saved} events saved")
        return {"status": "success", "events_saved": saved}
    except Exception as e:
        logger.error(f"GDELT ingestion task failed: {e}")
        return {"status": "failed", "error": str(e)}
