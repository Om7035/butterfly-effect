"""Event API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from butterfly.db.postgres import get_db
from butterfly.models.event import EventCreate, EventORM, EventResponse

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post("", response_model=dict)
async def create_event(event: EventCreate, db: AsyncSession = Depends(get_db)):
    """Create a new event.

    Args:
        event: Event data
        db: Database session

    Returns:
        Created event with ID and status
    """
    try:
        event_orm = EventORM(
            event_id=f"event_{uuid.uuid4().hex[:12]}",
            title=event.title,
            description=event.description,
            source=event.source,
            source_url=event.source_url,
            occurred_at=event.occurred_at,
            raw_text=event.raw_text,
            entities=[],
            processed=False,
        )
        db.add(event_orm)
        await db.commit()
        await db.refresh(event_orm)

        logger.info(f"Event created: {event_orm.event_id}")
        return {
            "event_id": event_orm.event_id,
            "status": "processing",
            "created_at": event_orm.created_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to create event: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create event") from None


@router.get("", response_model=dict)
async def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    source: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List events with pagination.

    Args:
        page: Page number (1-indexed)
        limit: Items per page
        source: Filter by source (optional)
        db: Database session

    Returns:
        Paginated list of events
    """
    try:
        # Build query
        stmt = select(EventORM)
        if source:
            stmt = stmt.where(EventORM.source == source)

        # Count total
        count_stmt = select(EventORM)
        if source:
            count_stmt = count_stmt.where(EventORM.source == source)
        count_result = await db.execute(count_stmt)
        total = len(count_result.fetchall())

        # Fetch paginated results
        stmt = stmt.order_by(desc(EventORM.created_at)).offset((page - 1) * limit).limit(limit)
        result = await db.execute(stmt)
        events = result.scalars().all()

        return {
            "items": [event.to_pydantic() for event in events],
            "total": total,
            "page": page,
            "pages": (total + limit - 1) // limit,
        }
    except Exception as e:
        logger.error(f"Failed to list events: {e}")
        raise HTTPException(status_code=500, detail="Failed to list events") from None


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single event by ID.

    Args:
        event_id: Event ID
        db: Database session

    Returns:
        Event details
    """
    try:
        stmt = select(EventORM).where(EventORM.event_id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return event.to_pydantic()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get event") from None
