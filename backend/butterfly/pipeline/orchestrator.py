
"""Analysis pipeline orchestrator.

Wires together all butterfly-effect modules into a single end-to-end pipeline:
  parsing → fetching → extracting → causal_modeling → simulating → extracting_chain → complete

Design principles:
  - Each stage is independently catchable — partial results are always returned
  - Progress is streamed via SSE (ProgressEvent) at every stage boundary
  - Results are cached in Redis (TTL 24h) — same question = instant answer
  - The pipeline is a pure async generator — no threads, no Celery needed for SSE
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime

from loguru import logger
from pydantic import BaseModel, Field

from butterfly.db.redis import get_cache, set_cache

# ── Stage constants ───────────────────────────────────────────────────────────

STAGES = [
    "parsing",
    "fetching",
    "extracting",
    "causal_modeling",
    "simulating",
    "extracting_chain",
    "complete",
]

STAGE_PERCENT = {
    "parsing":          10,
    "fetching":         25,
    "extracting":       40,
    "causal_modeling":  55,
    "simulating":       70,
    "extracting_chain": 85,
    "complete":         100,
}


# ── Pydantic models ───────────────────────────────────────────────────────────

class ProgressEvent(BaseModel):
    """One SSE progress event emitted during pipeline execution."""
    run_id: str
    stage: str
    percent: int
    message: str
    partial_result: dict | None = None


class AnalysisResult(BaseModel):
    """Full result of a completed analysis pipeline run."""
    run_id: str
    event: dict                                     # UniversalEvent.model_dump()
    stage: str = "complete"
    causal_chain: dict | None = None             # SimulationCausalChain
    evidence: list[dict] = Field(default_factory=list)
    graph_stats: dict = Field(default_factory=dict)
    simulation_diff: dict = Field(default_factory=dict)
    insights: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float = 0.0
    errors: list[str] = Field(default_factory=list)  # non-fatal stage errors


# ── Pipeline ──────────────────────────────────────────────────────────────────

class AnalysisPipeline:
    """Orchestrates the full butterfly-effect analysis pipeline.

    Usage:
        pipeline = AnalysisPipeline()
        async for event in pipeline.run("What happens if China invades Taiwan?"):
            send_sse(event)
    """

    async def run(self, raw_input: str) -> AsyncIterator[ProgressEvent]:
        """Run the full pipeline, yielding progress events at each stage.

        Args:
            raw_input: Plain-English question or event description

        Yields:
            ProgressEvent at each stage boundary
        """
        run_id = f"run_{uuid.uuid4().hex[:10]}"
        t_start = time.perf_counter()
        errors: list[str] = []

        logger.info(f"[{run_id}] Pipeline start: '{raw_input[:80]}'")

        # ── Cache check ───────────────────────────────────────────────────────
        cache_key = f"analyze:{_hash_input(raw_input)}"
        cached = await get_cache(cache_key)
        if cached:
            logger.info(f"[{run_id}] Cache hit — returning instantly")
            result = json.loads(cached)
            result["run_id"] = run_id  # fresh run_id for tracking
            yield ProgressEvent(
                run_id=run_id, stage="complete", percent=100,
                message="Loaded from cache",
                partial_result=result,
            )
            return

        # ── Stage 1: Parse ────────────────────────────────────────────────────
        yield ProgressEvent(run_id=run_id, stage="parsing", percent=10,
                            message="Understanding your question...")

        event = None
        try:
            from butterfly.llm.event_parser import EventParser
            event = await EventParser().parse(raw_input)
            logger.info(f"[{run_id}] Parsed: '{event.title}' domains={event.domain}")
            yield ProgressEvent(
                run_id=run_id, stage="parsing", percent=20,
                message=f"Identified: {event.title} · {', '.join(event.domain)}",
                partial_result={"event": event.model_dump(mode="json")},
            )
        except Exception as e:
            msg = f"Event parsing failed: {e}"
            logger.error(f"[{run_id}] {msg}")
            errors.append(msg)
            # Fall back to a minimal synthetic event so pipeline can continue
            event = _synthetic_event(raw_input)
            yield ProgressEvent(run_id=run_id, stage="parsing", percent=20,
                                message=f"Parsing degraded — using keyword extraction ({e})")

        # ── Stage 2: Fetch evidence ───────────────────────────────────────────
        yield ProgressEvent(run_id=run_id, stage="fetching", percent=25,
                            message=f"Gathering evidence from {len(event.domain)} domain sources...")

        evidence: list = []
        try:
            from butterfly.ingestion.universal_fetcher import UniversalFetcher
            evidence = await UniversalFetcher().fetch(event)
            yield ProgressEvent(
                run_id=run_id, stage="fetching", percent=35,
                message=f"Collected {len(evidence)} evidence items",
                partial_result={"evidence_count": len(evidence)},
            )
        except Exception as e:
            msg = f"Evidence fetch partial: {e}"
            logger.warning(f"[{run_id}] {msg}")
            errors.append(msg)
            yield ProgressEvent(run_id=run_id, stage="fetching", percent=35,
                                message=f"Evidence fetch degraded ({len(evidence)} items)")

        # ── Stage 3: Build graph ──────────────────────────────────────────────
        yield ProgressEvent(run_id=run_id, stage="extracting", percent=40,
                            message="Building causal knowledge graph...")

        graph_stats: dict = {}
        try:
            from butterfly.extraction.graph_builder import GraphBuilder
            result_gb = await GraphBuilder().build_from_text(
                event_id=f"evt_{run_id}",
                title=event.title,
                source="pipeline",
                occurred_at=event.occurred_at,
                raw_text=event.raw_input,
                domain=event.domain[0] if event.domain else "general",
            )
            graph_stats = {
                "nodes_created": result_gb.nodes_created,
                "edges_created": result_gb.edges_created,
            }
            yield ProgressEvent(
                run_id=run_id, stage="extracting", percent=50,
                message=f"Graph: {result_gb.nodes_created} nodes, {result_gb.edges_created} edges",
                partial_result={"graph_stats": graph_stats},
            )
        except Exception as e:
            msg = f"Graph build failed: {e}"
            logger.warning(f"[{run_id}] {msg}")
            errors.append(msg)
            yield ProgressEvent(run_id=run_id, stage="extracting", percent=50,
                                message="Graph build degraded — using seed structure")

        # ── Stage 4: Causal modeling ──────────────────────────────────────────
        yield ProgressEvent(run_id=run_id, stage="causal_modeling", percent=55,
                            message="Running causal identification...")

        causal_chain_dict: dict = {}
        try:
            from butterfly.causal.dag import DAGBuilder
            dag_builder = DAGBuilder()
            dag = await dag_builder.build_dag_for_event_with_template(
                f"evt_{run_id}", event.domain[0] if event.domain else "finance"
            )
            causal_chain_dict = {
                "nodes": [{"id": n, "label": n, "type": "entity"} for n in dag.get("nodes", [])[:10]],
                "edges": [
                    {"id": f"e{i}", "source": e[0], "target": e[1],
                     "type": "causal", "confidence": e[2] if len(e) > 2 else 0.7}
                    for i, e in enumerate(dag.get("edges", [])[:15])
                ],
                "total_hops": len(dag.get("edges", [])),
            }
            yield ProgressEvent(
                run_id=run_id, stage="causal_modeling", percent=65,
                message=f"DAG: {len(dag.get('nodes', []))} nodes, {len(dag.get('edges', []))} edges",
                partial_result={"causal_chain": causal_chain_dict},
            )
        except Exception as e:
            msg = f"Causal modeling failed: {e}"
            logger.warning(f"[{run_id}] {msg}")
            errors.append(msg)
            # Fall back to seed-based chain from event.causal_seeds
            causal_chain_dict = _seed_causal_chain(event)
            yield ProgressEvent(run_id=run_id, stage="causal_modeling", percent=65,
                                message="Causal modeling degraded — using seed chain")

        # ── Stage 5: Simulation ───────────────────────────────────────────────
        yield ProgressEvent(run_id=run_id, stage="simulating", percent=70,
                            message="Running agent-based simulation (A vs B)...")

        simulation_diff: dict = {}
        sim_log: list[dict] = []
        sim_tl_a: dict = {}
        sim_tl_b: dict = {}
        n_agents = 0

        try:
            from butterfly.simulation.universal_runner import UniversalRunner
            event_signal = _build_event_signal(event)
            sim_result = await UniversalRunner().run(
                event_title=event.title,
                event_domains=event.domain,
                event_signal=event_signal,
                steps=96,  # 96h for good chain depth; 168h in production
                use_llm=False,
            )
            simulation_diff = sim_result.get_diff()
            sim_log = sim_result.causal_log
            sim_tl_a = sim_result.timeline_a
            sim_tl_b = sim_result.timeline_b
            n_agents = sim_result.n_agents
            yield ProgressEvent(
                run_id=run_id, stage="simulating", percent=80,
                message=f"Simulation: {n_agents} agents, {sim_result.steps_completed} steps, "
                        f"{len(simulation_diff)} diverging variables",
                partial_result={"n_agents": n_agents, "diverging_vars": len(simulation_diff)},
            )
        except Exception as e:
            msg = f"Simulation failed: {e}"
            logger.warning(f"[{run_id}] {msg}")
            errors.append(msg)
            yield ProgressEvent(run_id=run_id, stage="simulating", percent=80,
                                message="Simulation degraded — skipping agent model")

        # ── Stage 6: Extract causal chain from simulation ─────────────────────
        yield ProgressEvent(run_id=run_id, stage="extracting_chain", percent=85,
                            message="Extracting causal chain from simulation logs...")

        final_chain: dict = causal_chain_dict
        try:
            if sim_log:
                from butterfly.causal.log_extractor import CausalLogExtractor
                chain_obj = CausalLogExtractor().extract(
                    log=sim_log,
                    timeline_a={int(k): v for k, v in sim_tl_a.items()},
                    timeline_b={int(k): v for k, v in sim_tl_b.items()},
                    event_title=event.title,
                    total_steps=48,
                )
                if chain_obj.total_hops > 0:
                    final_chain = chain_obj.model_dump()
                    # Merge with DAG-derived nodes for richer visualization
                    if causal_chain_dict.get("nodes"):
                        final_chain["nodes"] = causal_chain_dict["nodes"]
                        final_chain["edges"] = causal_chain_dict["edges"]

            yield ProgressEvent(
                run_id=run_id, stage="extracting_chain", percent=90,
                message=f"Chain: {final_chain.get('total_hops', len(final_chain.get('edges', [])))} hops, "
                        f"{len(final_chain.get('domain_coverage', []))} domains",
                partial_result={"causal_chain": final_chain},
            )
        except Exception as e:
            msg = f"Chain extraction failed: {e}"
            logger.warning(f"[{run_id}] {msg}")
            errors.append(msg)
            yield ProgressEvent(run_id=run_id, stage="extracting_chain", percent=90,
                                message="Chain extraction degraded — using DAG structure")

        # ── Stage 7: Generate insights ────────────────────────────────────────
        insights: list[str] = []
        try:
            from butterfly.llm.insight_generator import InsightGenerator
            insights = await InsightGenerator().generate_from_dict(final_chain, event)
        except Exception as e:
            logger.warning(f"[{run_id}] Insight generation failed: {e}")
            insights = _fallback_insights(event)

        # ── Complete ──────────────────────────────────────────────────────────
        duration = round(time.perf_counter() - t_start, 2)
        result = AnalysisResult(
            run_id=run_id,
            event=event.model_dump(mode="json"),
            stage="complete",
            causal_chain=final_chain,
            evidence=[e.model_dump(mode="json") for e in evidence[:10]],
            graph_stats=graph_stats,
            simulation_diff={k: dict(v) for k, v in simulation_diff.items()},
            insights=insights,
            duration_seconds=duration,
            errors=errors,
        )

        result_dict = result.model_dump(mode="json")

        # Cache by content hash (24h TTL)
        await set_cache(cache_key, json.dumps(result_dict), ttl=86400)
        # Also cache by run_id for retrieval
        await set_cache(f"analyze:run:{run_id}", json.dumps(result_dict), ttl=86400)

        logger.info(f"[{run_id}] Pipeline complete in {duration}s — "
                    f"{len(insights)} insights, {len(errors)} errors")

        yield ProgressEvent(
            run_id=run_id, stage="complete", percent=100,
            message=f"Analysis complete in {duration}s",
            partial_result=result_dict,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_input(text: str) -> str:
    """Stable hash of input for cache key."""
    import hashlib
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


def _build_event_signal(event) -> dict:
    """Derive simulation signal from event domains and severity."""
    severity_map = {"minor": 0.4, "moderate": 0.7, "major": 0.85, "catastrophic": 1.0}
    magnitude = severity_map.get(event.severity, 0.7)

    signal: dict = {"event_id": f"evt_{event.title[:20]}", "event_magnitude": magnitude}

    domain_signals = {
        "geopolitics":       {"conflict_intensity": magnitude, "oil_price": 80 + magnitude * 15},
        "military":          {"conflict_intensity": magnitude},
        "economics":         {"interest_rate_delta": magnitude * 0.75, "event_magnitude": magnitude},
        "financial_markets": {"interest_rate_delta": magnitude * 0.6, "risk_sentiment": 0.3},
        "energy":            {"oil_price": 80 + magnitude * 20, "conflict_intensity": magnitude * 0.5},
        "climate":           {"storm_intensity": magnitude, "infrastructure_damage": magnitude * 0.5},
        "health":            {"infection_rate": magnitude * 0.2, "event_magnitude": magnitude},
        "technology":        {"ai_capability_index": magnitude, "demand_shock": magnitude * 0.5},
        "trade":             {"interest_rate_delta": magnitude * 0.4, "risk_sentiment": 0.4},
        "humanitarian":      {"conflict_intensity": magnitude * 0.6, "displacement_count": magnitude * 50000},
    }

    for domain in event.domain:
        signal.update(domain_signals.get(domain, {}))

    return signal


def _seed_causal_chain(event) -> dict:
    """Build a minimal causal chain from event.causal_seeds."""
    nodes = [{"id": "n0", "type": "event", "label": event.title,
              "description": event.raw_input, "confidence": event.confidence}]
    edges = []
    prev = "n0"
    for i, seed in enumerate(event.causal_seeds[:5]):
        nid = f"n{i+1}"
        nodes.append({"id": nid, "type": "entity", "label": seed[:60],
                      "confidence": round(0.9 - i * 0.08, 2)})
        edges.append({"id": f"e{i}", "source": prev, "target": nid,
                      "type": "causal", "confidence": round(0.9 - i * 0.08, 2),
                      "latency_hours": [2, 24, 72, 168, 336][i]})
        prev = nid
    return {"nodes": nodes, "edges": edges,
            "total_hops": len(edges), "domain_coverage": event.domain}


def _fallback_insights(event) -> list[str]:
    """Rule-based insights when LLM is unavailable."""
    seeds = event.causal_seeds
    systems = event.affected_systems
    scope = event.geographic_scope
    return [
        f"What most people miss: {seeds[0] if seeds else 'first-order effects'} will manifest within 24-48 hours — before most analysts react.",
        f"What most people miss: [3rd order] {systems[0] if systems else 'the affected system'} is structurally exposed — this is the non-obvious vulnerability.",
        f"What most people miss: Geographic spillover to {scope[1] if len(scope) > 1 else 'neighboring regions'} is underpriced by markets.",
        f"What most people miss: [4th order] {event.domain[-1] if event.domain else 'downstream'} domain effects will peak 6-8 weeks after the initial event, not immediately.",
    ]


def _synthetic_event(raw_input: str):
    """Create a minimal UniversalEvent from raw text when LLM parsing fails."""
    from butterfly.llm.event_parser import UniversalEvent

    # Keyword-based domain detection — most specific first
    text_lower = raw_input.lower()
    domain = "economics"
    if any(w in text_lower for w in ["war", "conflict", "invasion", "attack", "military", "hamas", "israel", "ukraine", "russia", "nato", "troops", "missile"]):
        domain = "geopolitics"
    elif any(w in text_lower for w in ["hurricane", "earthquake", "flood", "storm", "climate", "wildfire", "tornado", "typhoon", "drought"]):
        domain = "climate"
    elif any(w in text_lower for w in ["virus", "pandemic", "outbreak", "disease", "pathogen", "epidemic", "covid", "mortality"]):
        domain = "health"
    elif any(w in text_lower for w in ["fed", "federal reserve", "fomc", "rate hike", "rate cut", "basis point", "bps", "inflation", "gdp", "recession", "mortgage", "treasury", "yield curve"]):
        domain = "economics"
    elif any(w in text_lower for w in ["ai", "openai", "chatgpt", "chip", "semiconductor", "tsmc", "nvidia", "software launch", "tech disruption"]):
        domain = "technology"

    # Build 3+ specific search queries from the input
    short = raw_input[:50].strip()
    queries = [
        short,
        f"{short} economic impact",
        f"{short} market reaction",
        f"{short} policy response",
    ]

    return UniversalEvent(
        raw_input=raw_input,
        title=raw_input[:60],
        domain=[domain],
        primary_actors=["Unknown Actor"],
        affected_systems=["Global Economy"],
        geographic_scope=["Global"],
        time_horizon="weeks",
        severity="moderate",
        causal_seeds=[
            "Initial shock to affected markets",
            "Supply chain disruption follows within 48-72 hours",
            "Policy response from governments and central banks",
        ],
        data_fetch_queries=queries,
        confidence=0.4,
    )
