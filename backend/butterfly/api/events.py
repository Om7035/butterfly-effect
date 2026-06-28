"""Event API routes — works with Postgres or SQLite fallback."""

import json
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from butterfly.db.postgres import get_db, _USE_SQLITE, _SQLITE_PATH
from butterfly.models.event import EventCreate, EventResponse

router = APIRouter(prefix="/api/v1/events", tags=["events"])


# ── SQLite helpers ────────────────────────────────────────────────────────────

async def _sqlite_create(event: EventCreate) -> dict:
    import aiosqlite
    event_id = f"event_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(_SQLITE_PATH) as db:
        await db.execute(
            """INSERT INTO events
               (event_id, title, description, source, source_url,
                occurred_at, raw_text, entities, processed, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                event_id, event.title, event.description, event.source,
                event.source_url, event.occurred_at.isoformat(),
                event.raw_text, "[]", 0, now,
            ),
        )
        await db.commit()
    return {"event_id": event_id, "status": "processing", "created_at": now}


async def _sqlite_list(page: int, limit: int, source: str | None) -> dict:
    import aiosqlite
    offset = (page - 1) * limit
    async with aiosqlite.connect(_SQLITE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if source:
            rows = await db.execute_fetchall(
                "SELECT * FROM events WHERE source=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (source, limit, offset),
            )
            count_row = await db.execute_fetchall(
                "SELECT COUNT(*) as c FROM events WHERE source=?", (source,)
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM events ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            count_row = await db.execute_fetchall("SELECT COUNT(*) as c FROM events")
    total = count_row[0]["c"] if count_row else 0
    items = [dict(r) for r in rows]
    for item in items:
        item["entities"] = json.loads(item.get("entities") or "[]")
        item["processed"] = bool(item.get("processed", 0))
    return {"items": items, "total": total, "page": page, "pages": max(1, (total + limit - 1) // limit)}


async def _sqlite_get(event_id: str) -> dict | None:
    import aiosqlite
    async with aiosqlite.connect(_SQLITE_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(
            "SELECT * FROM events WHERE event_id=?", (event_id,)
        )
    if not rows:
        return None
    item = dict(rows[0])
    item["entities"] = json.loads(item.get("entities") or "[]")
    item["processed"] = bool(item.get("processed", 0))
    return item


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=dict)
async def create_event(event: EventCreate, db=Depends(get_db)):
    try:
        if _USE_SQLITE or db is None:
            return await _sqlite_create(event)

        from butterfly.models.event import EventORM
        from sqlalchemy import select, desc
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
        return {
            "event_id": event_orm.event_id,
            "status": "processing",
            "created_at": event_orm.created_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"create_event failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=dict)
async def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    source: str | None = None,
    db=Depends(get_db),
):
    try:
        if _USE_SQLITE or db is None:
            return await _sqlite_list(page, limit, source)

        from butterfly.models.event import EventORM
        from sqlalchemy import select, desc, func
        stmt = select(EventORM)
        if source:
            stmt = stmt.where(EventORM.source == source)
        count_stmt = select(func.count()).select_from(EventORM)
        if source:
            count_stmt = count_stmt.where(EventORM.source == source)
        total = (await db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(desc(EventORM.created_at)).offset((page - 1) * limit).limit(limit)
        result = await db.execute(stmt)
        events = result.scalars().all()
        return {
            "items": [e.to_pydantic().model_dump() for e in events],
            "total": total,
            "page": page,
            "pages": max(1, (total + limit - 1) // limit),
        }
    except Exception as e:
        logger.error(f"list_events failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{event_id}")
async def get_event(event_id: str, db=Depends(get_db)):
    try:
        if _USE_SQLITE or db is None:
            item = await _sqlite_get(event_id)
            if not item:
                raise HTTPException(status_code=404, detail="Event not found")
            return item

        from butterfly.models.event import EventORM
        from sqlalchemy import select
        stmt = select(EventORM).where(EventORM.event_id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event.to_pydantic()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_event failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
