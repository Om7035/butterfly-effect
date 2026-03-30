"""POST /api/v1/analyze — Universal analysis endpoint.

Accepts any plain-English question, streams progress via SSE,
returns a full causal chain with evidence and insights.
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address

from butterfly.db.redis import get_cache

router = APIRouter(prefix="/api/v1", tags=["analyze"])
_limiter = Limiter(key_func=get_remote_address)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _stream(run_id: str, question: str):
    """Delegate to AnalysisPipeline and convert ProgressEvents to SSE bytes."""
    from butterfly.pipeline.orchestrator import AnalysisPipeline

    try:
        async for progress in AnalysisPipeline().run(question):
            payload = {
                "run_id": progress.run_id,
                "stage": progress.stage,
                "percent": progress.percent,
                "message": progress.message,
            }
            if progress.partial_result:
                if progress.stage == "complete":
                    payload["result"] = progress.partial_result
                else:
                    payload["partial"] = progress.partial_result
            yield _sse(payload)
    except Exception as e:
        logger.error(f"[{run_id}] Pipeline error: {e}")
        yield _sse({"run_id": run_id, "stage": "error", "percent": 0,
                    "message": str(e)})


@router.post("/analyze")
@_limiter.limit("5/minute")
async def analyze(request: Request, body: dict):
    """Universal analysis endpoint — accepts plain-English question or structured event.

    Returns Server-Sent Events stream with progress and final result.
    """
    question = (
        body.get("question")
        or body.get("raw_input")
        or body.get("title", "")
    )
    if not question:
        raise HTTPException(status_code=422, detail="'question' field is required")

    run_id = f"run_{uuid.uuid4().hex[:10]}"
    logger.info(f"[{run_id}] /analyze: '{question[:80]}'")

    return StreamingResponse(
        _stream(run_id, question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/analyze/{run_id}")
async def get_analysis(run_id: str):
    """Retrieve a cached analysis result by run_id."""
    cached = await get_cache(f"analyze:run:{run_id}")
    if not cached:
        raise HTTPException(status_code=404, detail="Analysis not found or expired")
    return json.loads(cached)
