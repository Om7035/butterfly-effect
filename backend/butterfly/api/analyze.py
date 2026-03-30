"""
POST /api/v1/analyze — Universal analysis endpoint.
Accepts any plain-English question, streams progress via SSE,
returns a full causal chain with evidence.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from slowapi import Limiter
from slowapi.util import get_remote_address

from butterfly.db.redis import get_cache, set_cache

router = APIRouter(prefix="/api/v1", tags=["analyze"])
_limiter = Limiter(key_func=get_remote_address)


# ── SSE helpers ───────────────────────────────────────────────────────────────

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _stream_pipeline(run_id: str, question: str):
    """Run the full analysis pipeline and yield SSE events."""

    async def emit(stage: str, percent: int, message: str, partial: dict | None = None):
        payload = {"run_id": run_id, "stage": stage, "percent": percent, "message": message}
        if partial:
            payload["partial"] = partial
        yield _sse(payload)

    # ── Stage 1: Parse event ──────────────────────────────────────────────────
    async for chunk in emit("parsing", 10, "Understanding your question…"):
        yield chunk

    event = None
    try:
        from butterfly.llm.event_parser import EventParser
        parser = EventParser()
        event = await parser.parse(question)
        async for chunk in emit("parsing", 20, f"Identified: {event.title} · domains: {', '.join(event.domain)}", {"event": event.model_dump(mode="json")}):
            yield chunk
    except Exception as e:
        logger.error(f"[{run_id}] Parsing failed: {e}")
        async for chunk in emit("error", 0, f"Could not parse event: {e}"):
            yield chunk
        return

    # ── Stage 2: Fetch evidence ───────────────────────────────────────────────
    async for chunk in emit("fetching", 25, f"Gathering evidence from {len(event.domain)} domain sources…"):
        yield chunk

    evidence = []
    try:
        from butterfly.ingestion.universal_fetcher import UniversalFetcher
        fetcher = UniversalFetcher()
        evidence = await fetcher.fetch(event)
        async for chunk in emit("fetching", 40, f"Collected {len(evidence)} evidence items", {"evidence_count": len(evidence)}):
            yield chunk
    except Exception as e:
        logger.warning(f"[{run_id}] Fetching partial failure: {e}")
        async for chunk in emit("fetching", 40, f"Evidence fetch partial ({e}) — continuing"):
            yield chunk

    # ── Stage 3: Build causal chain (demo/real) ───────────────────────────────
    async for chunk in emit("causal_modeling", 55, "Building causal graph…"):
        yield chunk

    causal_chain = _build_causal_chain(event, evidence)

    async for chunk in emit("causal_modeling", 70, f"Causal chain: {len(causal_chain['nodes'])} nodes, {len(causal_chain['edges'])} edges", {"graph": causal_chain}):
        yield chunk

    # ── Stage 4: Generate insights ────────────────────────────────────────────
    async for chunk in emit("insights", 80, "Generating non-obvious insights…"):
        yield chunk

    insights = await _generate_insights(event, causal_chain)

    async for chunk in emit("insights", 90, f"Generated {len(insights)} insights"):
        yield chunk

    # ── Stage 5: Complete ─────────────────────────────────────────────────────
    result = {
        "run_id": run_id,
        "event": event.model_dump(mode="json"),
        "causal_chain": causal_chain,
        "evidence": [e.model_dump(mode="json") for e in evidence[:10]],
        "insights": insights,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Cache result
    await set_cache(f"analyze:{run_id}", json.dumps(result), ttl=86400)

    async for chunk in emit("complete", 100, "Analysis complete", result):
        yield chunk


def _build_causal_chain(event, evidence: list) -> dict:
    """
    Build a causal chain from the event's causal_seeds.
    Uses evidence to enrich nodes where possible.
    Falls back to LLM-seeded structure when no real data is available.
    """
    from butterfly.llm.event_parser import UniversalEvent

    nodes = []
    edges = []

    # Root event node
    nodes.append({
        "id": "n0",
        "type": "event",
        "label": event.title,
        "description": event.raw_input,
        "confidence": event.confidence,
        "domain": event.domain,
    })

    # Build chain from causal_seeds
    prev_id = "n0"
    for i, seed in enumerate(event.causal_seeds[:6]):
        node_id = f"n{i+1}"

        # Determine node type from seed text
        seed_lower = seed.lower()
        if any(w in seed_lower for w in ["price", "rate", "index", "gdp", "inflation", "yield", "cost"]):
            ntype = "metric"
        elif any(w in seed_lower for w in ["government", "company", "bank", "fund", "org", "nation", "country"]):
            ntype = "entity"
        elif any(w in seed_lower for w in ["policy", "law", "sanction", "regulation", "treaty"]):
            ntype = "policy"
        else:
            ntype = "entity"

        # Try to find a matching evidence item
        evidence_match = next(
            (e for e in evidence if any(w in (e.title + e.content).lower() for w in seed_lower.split()[:3])),
            None,
        )

        nodes.append({
            "id": node_id,
            "type": ntype,
            "label": seed[:60],
            "description": evidence_match.content[:200] if evidence_match else seed,
            "confidence": round(0.9 - i * 0.08, 2),
            "source": evidence_match.source if evidence_match else None,
        })

        # Confidence decreases with each hop (butterfly effect uncertainty)
        confidence = round(0.92 - i * 0.08, 2)
        latency = [2, 24, 72, 168, 336, 720][i] if i < 6 else 720

        edges.append({
            "id": f"e{i}",
            "source": prev_id,
            "target": node_id,
            "type": "causal",
            "strength": confidence,
            "confidence": confidence,
            "latency_hours": latency,
        })
        prev_id = node_id

    # Add affected systems as entity nodes branching from n1
    for j, system in enumerate(event.affected_systems[:3]):
        sys_id = f"sys{j}"
        nodes.append({
            "id": sys_id,
            "type": "entity",
            "label": system[:60],
            "description": f"Affected system: {system}",
            "confidence": round(0.75 - j * 0.05, 2),
        })
        edges.append({
            "id": f"es{j}",
            "source": "n1",
            "target": sys_id,
            "type": "influence",
            "strength": 0.6,
            "confidence": 0.65,
            "latency_hours": 48,
        })

    return {"nodes": nodes, "edges": edges}


async def _generate_insights(event, causal_chain: dict) -> list[str]:
    """Generate non-obvious insights using Claude, or fall back to rule-based."""
    try:
        import anthropic
        from butterfly.config import settings

        if not settings.anthropic_api_key:
            raise RuntimeError("No API key")

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        chain_summary = "\n".join(
            f"  {e['source']} → {e['target']} (confidence: {e['confidence']}, latency: {e.get('latency_hours', '?')}h)"
            for e in causal_chain["edges"][:8]
        )
        node_labels = [n["label"] for n in causal_chain["nodes"]]

        prompt = f"""Event: {event.title}
Domain: {', '.join(event.domain)}
Severity: {event.severity}
Geographic scope: {', '.join(event.geographic_scope)}

Causal chain identified:
{chain_summary}

Nodes in chain: {', '.join(node_labels)}

Generate exactly 4 non-obvious insights about this causal chain.
Rules:
- Each insight must start with "What most people miss: "
- Reference a SPECIFIC hop in the chain (not vague)
- Flag 3rd/4th order effects explicitly with "[3rd order]" or "[4th order]"
- Be specific about timing ("within 6-8 weeks", not "soon")
- Name specific actors, not vague categories
- Flag uncertainty honestly

Respond with ONLY a JSON array of 4 strings."""

        resp = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        import re, json as _json
        raw = resp.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        insights = _json.loads(raw)
        return insights[:4] if isinstance(insights, list) else []

    except Exception as e:
        logger.warning(f"Insight generation failed ({e}), using rule-based fallback")
        # Rule-based fallback
        seeds = event.causal_seeds
        return [
            f"What most people miss: {seeds[0] if seeds else 'first-order effects'} will manifest within 24-48 hours, before most analysts react.",
            f"What most people miss: [3rd order] The {event.affected_systems[0] if event.affected_systems else 'affected system'} is structurally exposed — this is the non-obvious vulnerability.",
            f"What most people miss: Geographic spillover to {event.geographic_scope[1] if len(event.geographic_scope) > 1 else 'neighboring regions'} is underpriced by markets.",
            f"What most people miss: [4th order] The {event.domain[-1] if event.domain else 'downstream'} domain effects will peak 6-8 weeks after the initial event, not immediately.",
        ]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/analyze")
@_limiter.limit("10/minute")
async def analyze(request: Request, body: dict):
    """
    Universal analysis endpoint. Accepts plain-English question or structured event.
    Returns Server-Sent Events stream.
    """
    question = body.get("question") or body.get("raw_input") or body.get("title", "")
    if not question:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="'question' field is required")

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    logger.info(f"[{run_id}] Starting analysis: '{question[:80]}'")

    return StreamingResponse(
        _stream_pipeline(run_id, question),
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
    cached = await get_cache(f"analyze:{run_id}")
    if not cached:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Analysis not found or expired")
    import json
    return json.loads(cached)
