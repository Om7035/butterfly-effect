"""Simulation API routes — /api/v1/simulation."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import uuid
import json

from butterfly.db.postgres import get_db
from butterfly.db.redis import set_cache, get_cache
from butterfly.models.event import EventORM
from butterfly.simulation.runner import SimulationRunner

router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])
_runner = SimulationRunner()


@router.post("/run")
async def run_simulation(
    body: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Queue a simulation run for an event.

    Body: {event_id, n_agents: 100, steps: 168}
    Returns: {run_id, status: "queued", estimated_seconds: 120}
    """
    event_id = body.get("event_id")
    n_agents = int(body.get("n_agents", 100))
    steps = int(body.get("steps", 168))

    if not event_id:
        raise HTTPException(status_code=422, detail="event_id is required")

    stmt = select(EventORM).where(EventORM.event_id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    run_id = f"sim_{uuid.uuid4().hex[:12]}"

    # Build event signal from the event title/description heuristic
    event_signal = _build_event_signal(event_id, event.title)

    background_tasks.add_task(_run_simulation_bg, run_id, event_signal, steps, n_agents)

    return {
        "run_id": run_id,
        "event_id": event_id,
        "status": "queued",
        "estimated_seconds": max(30, steps // 10),
    }


@router.get("/{run_id}")
async def get_simulation(run_id: str):
    """Get simulation status and results."""
    status = await get_cache(f"sim:{run_id}:status")
    if not status:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if status == "running":
        return {"run_id": run_id, "status": "running"}

    if status == "failed":
        error = await get_cache(f"sim:{run_id}:error") or "Unknown error"
        return {"run_id": run_id, "status": "failed", "error": error}

    cached = await get_cache(f"sim:{run_id}:result")
    if not cached:
        return {"run_id": run_id, "status": status}

    return json.loads(cached)


@router.get("/{run_id}/diff")
async def get_simulation_diff(run_id: str):
    """Get the A vs B diff for a completed simulation."""
    cached = await get_cache(f"sim:{run_id}:result")
    if not cached:
        raise HTTPException(status_code=404, detail="Simulation result not found")

    data = json.loads(cached)
    tl_a = data.get("timeline_a", {})
    tl_b = data.get("timeline_b", {})

    diff: dict[str, dict] = {}
    for metric in set(list(tl_a.keys()) + list(tl_b.keys())):
        a_val = tl_a.get(metric, {})
        b_val = tl_b.get(metric, {})
        if isinstance(a_val, dict) and isinstance(b_val, dict):
            diff[metric] = {
                k: round(float(a_val.get(k, 0)) - float(b_val.get(k, 0)), 4)
                for k in set(list(a_val.keys()) + list(b_val.keys()))
            }

    return {
        "run_id": run_id,
        "timeline_a": tl_a,
        "timeline_b": tl_b,
        "diff": diff,
        "duration_seconds": data.get("duration_seconds"),
        "steps_completed": data.get("steps_completed"),
    }


async def _run_simulation_bg(
    run_id: str, event_signal: dict, steps: int, n_agents: int
) -> None:
    """Background task: run simulation and cache result."""
    try:
        await set_cache(f"sim:{run_id}:status", "running", ttl=3600)

        # Distribute agents
        n_market = max(1, int(n_agents * 0.50))
        n_housing = max(1, int(n_agents * 0.30))
        n_supply = max(1, int(n_agents * 0.15))
        n_policy = max(1, n_agents - n_market - n_housing - n_supply)

        result = await _runner.run_parallel(
            event_signal=event_signal,
            steps=steps,
            n_market=n_market,
            n_housing=n_housing,
            n_supply=n_supply,
            n_policy=n_policy,
        )

        await set_cache(f"sim:{run_id}:result", result.model_dump_json(), ttl=7200)
        await set_cache(f"sim:{run_id}:status", "complete", ttl=7200)
        logger.info(f"Simulation {run_id} complete in {result.duration_seconds}s")

    except Exception as e:
        logger.error(f"Simulation {run_id} failed: {e}")
        await set_cache(f"sim:{run_id}:status", "failed", ttl=3600)
        await set_cache(f"sim:{run_id}:error", str(e), ttl=3600)


def _build_event_signal(event_id: str, title: str) -> dict:
    """Derive simulation signal from event title heuristics."""
    title_lower = title.lower()
    rate_delta = 0.0
    mortgage_delta = 0.0
    commodity_delta = 0.0

    if any(w in title_lower for w in ["rate", "fed", "fomc", "hike", "basis"]):
        rate_delta = 0.75   # Default 75bps hike
        mortgage_delta = rate_delta * 2.57

    if any(w in title_lower for w in ["energy", "oil", "gas", "commodity"]):
        commodity_delta = 0.3

    return {
        "event_id": event_id,
        "rate_delta": rate_delta,
        "mortgage_delta": mortgage_delta,
        "commodity_delta": commodity_delta,
    }
