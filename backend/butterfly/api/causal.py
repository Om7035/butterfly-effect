"""Causal analysis API routes."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import uuid

from butterfly.db.postgres import get_db
from butterfly.db.redis import set_cache, get_cache
from butterfly.models.event import EventORM
from butterfly.models.causal_edge import CounterfactualResult
from butterfly.causal.counterfactual import CounterfactualEngine
import json

router = APIRouter(prefix="/api/v1/causal", tags=["causal"])
engine = CounterfactualEngine()


@router.post("/analyze")
async def start_analysis(
    body: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Queue a causal analysis job for an event.

    Body: {"event_id": str, "horizon_hours": int (optional, default 168)}
    """
    event_id = body.get("event_id")
    horizon_hours = int(body.get("horizon_hours", 168))

    if not event_id:
        raise HTTPException(status_code=422, detail="event_id is required")

    # Verify event exists
    stmt = select(EventORM).where(EventORM.event_id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    job_id = f"job_{uuid.uuid4().hex[:12]}"

    # Run analysis in background
    background_tasks.add_task(_run_analysis, event_id, horizon_hours, job_id)

    return {"job_id": job_id, "event_id": event_id, "status": "queued"}


async def _run_analysis(event_id: str, horizon_hours: int, job_id: str) -> None:
    """Background task: run counterfactual and cache result."""
    try:
        await set_cache(f"job:{job_id}:status", "running", ttl=3600)
        result = await engine.run_counterfactual(event_id, horizon_hours)
        result_json = result.model_dump_json()
        await set_cache(f"causal:{event_id}", result_json, ttl=3600)
        await set_cache(f"job:{job_id}:status", "complete", ttl=3600)
        await set_cache(f"job:{job_id}:event_id", event_id, ttl=3600)
        logger.info(f"Causal analysis complete for {event_id}")
    except Exception as e:
        logger.error(f"Causal analysis failed for {event_id}: {e}")
        await set_cache(f"job:{job_id}:status", "failed", ttl=3600)
        await set_cache(f"job:{job_id}:error", str(e), ttl=3600)


@router.get("/{event_id}")
async def get_causal_chain(event_id: str):
    """Get the causal chain result for an event."""
    cached = await get_cache(f"causal:{event_id}")
    if not cached:
        raise HTTPException(
            status_code=404,
            detail="No causal analysis found. POST /api/v1/causal/analyze first.",
        )
    try:
        return json.loads(cached)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse cached result")


@router.get("/{event_id}/edges")
async def get_causal_edges(event_id: str):
    """Get all causal edges for an event."""
    cached = await get_cache(f"causal:{event_id}")
    if not cached:
        raise HTTPException(status_code=404, detail="No causal analysis found")
    try:
        data = json.loads(cached)
        return {"event_id": event_id, "edges": data.get("causal_edges", [])}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse cached result")


@router.get("/{event_id}/diff")
async def get_counterfactual_diff(event_id: str):
    """Get the counterfactual diff (Timeline A - Timeline B) for an event."""
    cached = await get_cache(f"causal:{event_id}")
    if not cached:
        raise HTTPException(status_code=404, detail="No causal analysis found")
    try:
        data = json.loads(cached)
        return {
            "event_id": event_id,
            "timeline_a": data.get("timeline_a", {}),
            "timeline_b": data.get("timeline_b", {}),
            "diff": data.get("diff", {}),
            "peak_delta_at_hours": data.get("peak_delta_at_hours", {}),
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse cached result")


@router.get("/{event_id}/evidence")
async def get_evidence_paths(event_id: str):
    """Get evidence paths for all causal edges."""
    cached = await get_cache(f"causal:{event_id}")
    if not cached:
        raise HTTPException(status_code=404, detail="No causal analysis found")
    try:
        data = json.loads(cached)
        edges = data.get("causal_edges", [])
        evidence = [
            {
                "edge_id": e.get("edge_id"),
                "source": e.get("source_node_id"),
                "target": e.get("target_node_id"),
                "evidence_path": e.get("evidence_path", []),
                "strength_score": e.get("strength_score"),
                "refutation_passed": e.get("refutation_passed"),
            }
            for e in edges
        ]
        return {"event_id": event_id, "evidence": evidence}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse cached result")
