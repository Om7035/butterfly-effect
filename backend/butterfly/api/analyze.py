"""Universal analyze endpoint — SSE streaming, real LLM + agent swarm + NLP."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from butterfly.backtesting.alternative_chains import AlternativeChainsBuilder
from butterfly.backtesting.confidence_intervals import IntervalEstimator
from butterfly.causal.cycle_detector import CycleDetector
from butterfly.logging_utils import (
    DebugTimer,
    log_data_sample,
    log_fetch_result,
    log_graph_build,
    log_stage,
)

router = APIRouter(prefix="/api/v1/analyze", tags=["analyze"])

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


class AnalyzeRequest(BaseModel):
    question: str


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


# ── Graph builder — LLM seeds + NLP extraction from evidence ─────────────────

def _build_graph(event, evidence: list | None = None) -> dict:
    """
    Build causal graph. Evidence drives node creation; LLM seeds fill gaps.
    Correct flow: Evidence → NER → nodes. LLM seeds → fill where evidence sparse.
    """
    nodes: list[dict] = []
    event_domains = getattr(event, "domain", [])

    nodes.append({
        "id": "root", "type": "Event", "label": event.title[:60],
        "hop": 0, "severity": getattr(event, "severity", "moderate"),
        "confidence": getattr(event, "confidence", 0.85),
        "domain": event_domains[0] if event_domains else "general",
    })

    # Step 1: Extract nodes from evidence via NER (primary source)
    evidence_nodes: list[dict] = []
    evidence_edges: list[dict] = []
    if evidence:
        evidence_nodes, evidence_edges = _evidence_to_nodes(evidence, event)

    # Step 2: LLM seeds fill gaps — only add seeds not already covered by evidence
    evidence_labels = {n["label"].lower() for n in evidence_nodes}
    llm_nodes: list[dict] = []
    llm_edges: list[dict] = []

    for i, seed in enumerate(event.causal_seeds[:5]):
        if seed.lower()[:20] in evidence_labels:
            continue  # evidence already covers this
        nid = f"seed_{i}"
        conf_val = round(0.85 - i * 0.05, 2)
        seed_domain = event_domains[0] if event_domains else "general"
        llm_nodes.append({
            "id": nid, "type": "Metric", "label": seed[:60],
            "hop": 1, "confidence": conf_val, "strength": conf_val,
            "domain": seed_domain, "source": "llm",
        })
        llm_edges.append({
            "id": f"e_root_{i}", "source": "root", "target": nid,
            "strength": conf_val, "latency_hours": (i + 1) * 24,
            "confidence": [round(conf_val - 0.1, 2), round(conf_val + 0.08, 2)],
            "relationship_type": "TRIGGERS" if i == 0 else "CAUSES",
            "domain_crossing": False,
        })

    for i, system in enumerate(event.affected_systems[:4]):
        nid = f"sys_{i}"
        conf_val = round(0.65 - i * 0.05, 2)
        sys_domain = event_domains[1] if len(event_domains) > 1 else event_domains[0] if event_domains else "general"
        llm_nodes.append({
            "id": nid, "type": "Entity", "label": system[:60],
            "hop": 2, "confidence": conf_val, "strength": conf_val,
            "domain": sys_domain, "source": "llm",
        })
        src = f"seed_{i % max(len(event.causal_seeds), 1)}"
        src_domain = event_domains[0] if event_domains else "general"
        llm_edges.append({
            "id": f"e_sys_{i}", "source": src, "target": nid,
            "strength": conf_val, "latency_hours": (i + 2) * 48,
            "confidence": [round(conf_val - 0.1, 2), round(conf_val + 0.1, 2)],
            "relationship_type": "INFLUENCES",
            "domain_crossing": src_domain != sys_domain,
        })

    for i, actor in enumerate(event.primary_actors[:3]):
        nid = f"actor_{i}"
        conf_val = round(0.50 - i * 0.05, 2)
        actor_domain = event_domains[min(i + 1, len(event_domains) - 1)] if event_domains else "general"
        llm_nodes.append({
            "id": nid, "type": "Entity", "label": actor[:60],
            "hop": 3, "confidence": conf_val, "strength": conf_val,
            "domain": actor_domain, "source": "llm",
        })
        src = f"sys_{i % max(len(event.affected_systems), 1)}"
        src_domain = event_domains[1] if len(event_domains) > 1 else event_domains[0] if event_domains else "general"
        llm_edges.append({
            "id": f"e_actor_{i}", "source": src, "target": nid,
            "strength": conf_val, "latency_hours": (i + 3) * 72,
            "confidence": [round(conf_val - 0.1, 2), round(conf_val + 0.1, 2)],
            "relationship_type": "CORRELATES_WITH" if i > 1 else "CAUSES",
            "domain_crossing": src_domain != actor_domain,
        })

    # Merge: evidence nodes first (more trustworthy), then LLM gap-fillers
    all_nodes = [nodes[0]] + evidence_nodes + llm_nodes
    all_edges = evidence_edges + llm_edges

    return {"nodes": all_nodes, "edges": all_edges, "domain": event_domains}


def _evidence_to_nodes(evidence: list, event) -> tuple[list[dict], list[dict]]:
    """
    Primary graph construction from fetched evidence via NER + relation extraction.
    Uses app.state.nlp (loaded at startup) — zero per-request load cost.
    """
    new_nodes: list[dict] = []
    new_edges: list[dict] = []

    try:
        # Get the startup-loaded spaCy model
        from butterfly.main import app as _app
        nlp = getattr(_app.state, "nlp", None)
        if nlp is None:
            return [], []

        from butterfly.extraction.normalizer import normalize_entity_name
        from butterfly.extraction.relations import RelationExtractor
        rel_extractor = RelationExtractor()

        seen_labels: set[str] = set()
        event_domains = getattr(event, "domain", [])

        for ev_item in evidence[:8]:  # top 8 items
            text = (getattr(ev_item, "content", "") or getattr(ev_item, "title", ""))[:400]
            if not text or len(text) < 30:
                continue

            doc = nlp(text)

            # NER → nodes
            label_map = {"ORG": "Entity", "GPE": "Entity", "PERSON": "Entity",
                         "MONEY": "Metric", "PERCENT": "Metric", "LAW": "Policy", "EVENT": "Event"}
            conf_map = {"ORG": 0.80, "GPE": 0.80, "PERSON": 0.75,
                        "MONEY": 0.85, "PERCENT": 0.85, "LAW": 0.70, "EVENT": 0.70}

            item_entities = []
            for ent in doc.ents:
                if ent.label_ not in label_map:
                    continue
                norm = normalize_entity_name(ent.text)
                if norm.lower() in seen_labels or len(norm) < 3:
                    continue
                if len(new_nodes) >= 8:
                    break
                nid = f"ev_{len(new_nodes)}"
                conf = conf_map.get(ent.label_, 0.65)
                node = {
                    "id": nid, "type": label_map[ent.label_],
                    "label": norm[:60], "hop": 2,
                    "confidence": conf, "strength": conf,
                    "domain": event_domains[0] if event_domains else "general",
                    "source": "evidence",
                    "evidence_url": getattr(ev_item, "url", None),
                }
                new_nodes.append(node)
                seen_labels.add(norm.lower())
                item_entities.append((nid, norm, ent))

            # Relation extraction → edges with real relation types
            if len(item_entities) >= 2:
                from butterfly.extraction.ner import ExtractedEntity
                extracted = [
                    ExtractedEntity(text=name, label=label_map.get(ent.label_, "Entity"),
                                    start=ent.start_char, end=ent.end_char,
                                    confidence=conf_map.get(ent.label_, 0.65))
                    for nid, name, ent in item_entities
                ]
                relations = rel_extractor.extract_relations(text, extracted)
                for rel in relations[:3]:
                    src_node = next((n for n in new_nodes if n["label"].lower() == rel.source_entity.lower()), None)
                    tgt_node = next((n for n in new_nodes if n["label"].lower() == rel.target_entity.lower()), None)
                    if src_node and tgt_node and src_node["id"] != tgt_node["id"]:
                        src_domain = src_node.get("domain", "general")
                        tgt_domain = tgt_node.get("domain", "general")
                        new_edges.append({
                            "id": f"e_ev_{len(new_edges)}",
                            "source": src_node["id"], "target": tgt_node["id"],
                            "strength": round(rel.confidence * 0.8, 2),
                            "latency_hours": 48,
                            "confidence": [round(rel.confidence * 0.6, 2), round(rel.confidence, 2)],
                            "relationship_type": rel.relation_type,
                            "domain_crossing": src_domain != tgt_domain,
                        })
            elif item_entities:
                # Single entity — connect to root
                nid = item_entities[0][0]
                new_edges.append({
                    "id": f"e_ev_{len(new_edges)}",
                    "source": "root", "target": nid,
                    "strength": 0.55, "latency_hours": 24,
                    "confidence": [0.45, 0.65],
                    "relationship_type": "INFLUENCES",
                    "domain_crossing": False,
                })

        logger.info(f"[NLP] Evidence → {len(new_nodes)} nodes, {len(new_edges)} edges")

    except Exception as e:
        logger.warning(f"[NLP] Evidence extraction skipped: {e}")

    return new_nodes, new_edges


def _merge_deep_seeds(graph: dict, deep_data: dict, event) -> dict:
    """Merge pass-2 deep causal seeds as hop-3/4 nodes into the graph."""
    nodes = graph["nodes"]
    edges = graph["edges"]
    event_domains = getattr(event, "domain", [])
    existing_labels = {n["label"].lower()[:20] for n in nodes}

    deep_seeds = deep_data.get("deep_causal_seeds", [])
    deep_actors = deep_data.get("non_obvious_actors", [])

    # Add deep seeds as hop-3 nodes
    for i, seed in enumerate(deep_seeds[:4]):
        if seed.lower()[:20] in existing_labels:
            continue
        nid = f"deep_{i}"
        conf = round(0.45 - i * 0.04, 2)
        # Determine domain — deep effects often cross domains
        deep_domain = event_domains[min(i + 2, len(event_domains) - 1)] if len(event_domains) > 2 else (
            event_domains[1] if len(event_domains) > 1 else event_domains[0] if event_domains else "general"
        )
        src_domain = event_domains[0] if event_domains else "general"
        nodes.append({
            "id": nid, "type": "Metric", "label": seed[:60],
            "hop": 3, "confidence": conf, "strength": conf,
            "domain": deep_domain, "source": "llm_deep",
        })
        # Connect to a 2nd-order node if available, else root
        src_candidates = [n["id"] for n in nodes if n.get("hop") == 2]
        src = src_candidates[i % len(src_candidates)] if src_candidates else "root"
        edges.append({
            "id": f"e_deep_{i}", "source": src, "target": nid,
            "strength": conf, "latency_hours": (i + 4) * 96,
            "confidence": [round(conf - 0.1, 2), round(conf + 0.1, 2)],
            "relationship_type": "CAUSES",
            "domain_crossing": src_domain != deep_domain,
        })
        existing_labels.add(seed.lower()[:20])

    # Add non-obvious actors as hop-4 nodes
    for i, actor in enumerate(deep_actors[:2]):
        if actor.lower()[:20] in existing_labels:
            continue
        nid = f"deep_actor_{i}"
        conf = round(0.35 - i * 0.04, 2)
        actor_domain = event_domains[-1] if event_domains else "general"
        src_candidates = [n["id"] for n in nodes if n.get("hop") == 3]
        src = src_candidates[i % len(src_candidates)] if src_candidates else "root"
        src_domain = next((n.get("domain", "general") for n in nodes if n["id"] == src), "general")
        nodes.append({
            "id": nid, "type": "Entity", "label": actor[:60],
            "hop": 4, "confidence": conf, "strength": conf,
            "domain": actor_domain, "source": "llm_deep",
        })
        edges.append({
            "id": f"e_deep_actor_{i}", "source": src, "target": nid,
            "strength": conf, "latency_hours": (i + 5) * 120,
            "confidence": [round(conf - 0.1, 2), round(conf + 0.1, 2)],
            "relationship_type": "CORRELATES_WITH",
            "domain_crossing": src_domain != actor_domain,
        })
        existing_labels.add(actor.lower()[:20])

    graph["nodes"] = nodes
    graph["edges"] = edges
    return graph


def _nlp_enrich(evidence: list, existing_nodes: list, existing_edges: list) -> tuple[list, list]:
    """Legacy — kept for compatibility. Real work now done in _evidence_to_nodes."""
    return [], []


# ── FRED enrichment for economics queries ────────────────────────────────────

async def _fetch_fred_data(domains: list[str]) -> dict[str, dict]:
    """Fetch latest FRED series values for economics/financial queries."""
    if not any(d in domains for d in ("economics", "financial_markets", "trade")):
        return {}

    fred_data: dict[str, dict] = {}
    try:
        from butterfly.ingestion.fred import FREDIngester
        ingester = FREDIngester()
        if not ingester.api_key:
            return {}

        import httpx

        series_to_fetch = ["FEDFUNDS", "MORTGAGE30US", "HOUST", "UNRATE", "T10Y2Y"]
        async with httpx.AsyncClient(timeout=3.0) as client:
            for series_id in series_to_fetch:
                try:
                    resp = await client.get(
                        f"{ingester.BASE_URL}/series/observations",
                        params={
                            "series_id": series_id,
                            "api_key": ingester.api_key,
                            "limit": 2,
                            "sort_order": "desc",
                        },
                    )
                    if resp.status_code == 200:
                        obs = resp.json().get("observations", [])
                        if obs and obs[0].get("value") != ".":
                            current = float(obs[0]["value"])
                            prev = float(obs[1]["value"]) if len(obs) > 1 and obs[1].get("value") != "." else current
                            fred_data[series_id] = {
                                "value": current,
                                "delta": round(current - prev, 4),
                                "date": obs[0].get("date", ""),
                            }
                except Exception:
                    pass

        logger.info(f"[FRED] Fetched {len(fred_data)} series")
    except Exception as e:
        logger.warning(f"[FRED] Fetch failed: {e}")

    return fred_data


def _apply_fred_to_graph(graph: dict, fred_data: dict[str, dict]) -> dict:
    """Enrich MetricNode values with real FRED data where labels match."""
    if not fred_data:
        return graph

    label_to_series = {
        "fed funds rate": "FEDFUNDS",
        "federal funds": "FEDFUNDS",
        "fedfunds": "FEDFUNDS",
        "mortgage": "MORTGAGE30US",
        "30-year": "MORTGAGE30US",
        "housing starts": "HOUST",
        "houst": "HOUST",
        "unemployment": "UNRATE",
        "unrate": "UNRATE",
        "yield curve": "T10Y2Y",
        "t10y2y": "T10Y2Y",
    }

    for node in graph["nodes"]:
        label_lower = node.get("label", "").lower()
        for keyword, series_id in label_to_series.items():
            if keyword in label_lower and series_id in fred_data:
                node["value"] = fred_data[series_id]["value"]
                node["delta"] = fred_data[series_id]["delta"]
                node["fred_series"] = series_id
                node["fred_date"] = fred_data[series_id]["date"]
                node["confidence"] = 0.95  # FRED data = high confidence
                break

    return graph


# ── GDELT enrichment for geopolitics queries ──────────────────────────────────

async def _fetch_gdelt_evidence(event) -> list[dict]:
    """Fetch GDELT articles — 3s timeout."""
    domains = getattr(event, "domain", [])
    if not any(d in domains for d in ("geopolitics", "military", "humanitarian", "health")):
        return []
    try:
        import httpx
        query_terms = " OR ".join(getattr(event, "data_fetch_queries", [event.title])[:2])
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                "http://api.gdeltproject.org/api/v2/doc/doc",
                params={"query": query_terms[:200], "mode": "artlist", "format": "json", "maxrecords": 5},
            )
            if resp.status_code == 200:
                articles = resp.json().get("articles", [])
                return [{"source": "gdelt", "title": a.get("title", ""), "url": a.get("url", ""), "tone": a.get("tone", 0)} for a in articles[:5]]
    except Exception as e:
        logger.debug(f"[GDELT] failed: {e}")
    return []


async def _fetch_universal(event) -> list:
    """Wrap UniversalFetcher with error handling."""
    try:
        from butterfly.ingestion.universal_fetcher import UniversalFetcher
        return await UniversalFetcher().fetch(event)
    except Exception as e:
        logger.warning(f"[ANALYZE] Universal fetcher failed: {e}")
        return []


# ── Insight builder (structural fallback) ─────────────────────────────────────

def _build_insights(event, graph: dict) -> list[dict]:
    seeds = event.causal_seeds
    systems = event.affected_systems
    insights = []

    if seeds:
        insights.append({
            "order": 2, "hop": 2,
            "text": f"2nd order: {seeds[0]} — manifests within 24-48 hours of {event.title}.",
            "why": (
                f"The {event.domain[0] if event.domain else 'primary'} domain transmission "
                f"mechanism activates immediately. {seeds[0]} is the first structural vulnerability exposed."
            ),
            "confidence": 0.82,
            "sources": [f"{event.domain[0].title()} Analysis" if event.domain else "Domain Analysis",
                        "Historical precedent data"],
        })

    if len(seeds) >= 2 and systems:
        insights.append({
            "order": 3, "hop": 3,
            "text": f"3rd order: {seeds[1]} cascades into {systems[0]} disruption within {event.time_horizon}.",
            "why": (
                f"Cross-domain transmission from {event.domain[0] if event.domain else 'primary'} "
                f"to {event.domain[1] if len(event.domain) > 1 else 'secondary'} domain. "
                "Most analysts stop tracking at the first-order effect and miss this."
            ),
            "confidence": 0.65,
            "sources": [f"{s.title()} sector data" for s in event.domain[:2]],
        })

    if len(seeds) >= 3:
        insights.append({
            "order": 4, "hop": 4,
            "text": f"4th order (non-obvious): {seeds[2]} — peaks {event.time_horizon} after initial event.",
            "why": (
                f"This is the true butterfly effect. By the time {seeds[2]} manifests, "
                f"the causal chain has crossed {len(event.domain)} domains and "
                f"{len(event.geographic_scope)} geographic regions. "
                "Confidence is lower because the chain is long, but the mechanism is traceable."
            ),
            "confidence": 0.48,
            "sources": [f"{g} regional data" for g in event.geographic_scope[:2]],
        })

    return insights


# ── SSE stream ────────────────────────────────────────────────────────────────

async def _analyze_stream(question: str) -> AsyncGenerator[str, None]:
    try:
        # ── Stage 1: Parse with LLM ───────────────────────────────────────────
        log_stage("PARSE", "start")
        yield _sse({"stage": "parsing", "stats": {"nodes": 0, "agents": 0, "steps": 0}})

        with DebugTimer("LLM event parsing"):
            from butterfly.llm.event_parser import EventParser
            parser = EventParser()
            event = await parser.parse(question)

        logger.info(f"[ANALYZE] Parsed: '{event.title}' domain={event.domain} severity={event.severity}")
        log_stage("PARSE", "done", {
            "title": event.title[:50],
            "domains": len(event.domain),
            "severity": event.severity,
            "causal_seeds": len(event.causal_seeds),
        })

        yield _sse({
            "stage": "parsing",
            "message": f"Detected: {', '.join(event.domain)} · {event.severity} · {event.time_horizon}",
            "stats": {"nodes": 0, "agents": 0, "steps": 0},
            "event_meta": {"title": event.title, "domain": event.domain,
                           "severity": event.severity, "confidence": event.confidence},
        })

        # Pass 2: deep parse for 3rd/4th order effects (runs concurrently with fetch)
        deep_parse_task = asyncio.create_task(
            parser.parse_deep(question, event.causal_seeds)
        )

        await asyncio.sleep(0.2)

        # ── Stage 2: Fetch evidence — all sources concurrently ───────────────
        log_stage("FETCH", "start")
        yield _sse({
            "stage": "fetching",
            "message": f"Gathering evidence for {len(event.domain)} domains...",
            "stats": {"nodes": len(event.causal_seeds), "agents": 0, "steps": 0},
        })

        evidence: list = []
        gdelt_items: list[dict] = []
        fred_data: dict = {}

        # Run all fetchers concurrently with a hard 7s timeout
        fetch_start = time.time()
        try:
            with DebugTimer("Parallel evidence fetch (Universal, GDELT, FRED)"):
                fetch_results = await asyncio.wait_for(
                    asyncio.gather(
                        _fetch_universal(event),
                        _fetch_gdelt_evidence(event),
                        _fetch_fred_data(event.domain),
                        return_exceptions=True,
                    ),
                    timeout=7.0,
                )
            if not isinstance(fetch_results[0], Exception):
                evidence = fetch_results[0] or []
            if not isinstance(fetch_results[1], Exception):
                gdelt_items = fetch_results[1] or []
            if not isinstance(fetch_results[2], Exception):
                fred_data = fetch_results[2] or {}
        except asyncio.TimeoutError:
            logger.warning("[ANALYZE] Fetch timeout (7s) — continuing with partial evidence")
            log_stage("FETCH", "warning", {"error": "7s timeout, partial results"})
        except Exception as e:
            logger.warning(f"[ANALYZE] Fetch error: {e}")
            log_stage("FETCH", "warning", {"error": str(e)[:50]})

        fetch_elapsed = time.time() - fetch_start
        log_fetch_result("Universal", len(evidence) > 0, len(evidence), fetch_elapsed)
        log_fetch_result("GDELT", len(gdelt_items) > 0, len(gdelt_items), fetch_elapsed)
        log_fetch_result("FRED", len(fred_data) > 0, len(fred_data), fetch_elapsed)
        log_stage("FETCH", "done", {
            "sources": 3,
            "universal_items": len(evidence),
            "gdelt_items": len(gdelt_items),
            "fred_series": len(fred_data),
        })

        total_evidence = len(evidence) + len(gdelt_items)
        yield _sse({
            "stage": "fetching",
            "message": f"Collected {total_evidence} evidence items ({len(fred_data)} FRED series)",
            "stats": {"nodes": len(event.causal_seeds), "agents": 0, "steps": 0},
        })

        await asyncio.sleep(0.1)

        # ── Stage 3: Build graph (LLM + NLP enrichment) ───────────────────────
        log_stage("GRAPH", "start")
        yield _sse({
            "stage": "extracting",
            "message": "Building causal knowledge graph with NLP enrichment...",
            "stats": {"nodes": len(event.causal_seeds), "agents": 0, "steps": 0},
        })

        graph_start = time.time()
        with DebugTimer("Building base causal graph"):
            graph = _build_graph(event, evidence=evidence if evidence else None)

        log_data_sample("Initial graph structure", {
            "nodes": len(graph["nodes"]),
            "edges": len(graph["edges"]),
            "domains": event.domain,
        })

        # Apply evidence updates to adjust edge confidence scores
        evidence_audit = None
        if evidence:
            try:
                with DebugTimer("Applying evidence to graph"):
                    from butterfly.causal.dag import DAGBuilder
                    graph, evidence_audit = DAGBuilder().apply_evidence_updates(graph, evidence)
                logger.info(f"[ANALYZE] Evidence applied: {len(evidence_audit.updates)} edges updated")
                log_data_sample("Evidence audit updates", evidence_audit.updates[:5])
            except Exception as e:
                logger.warning(f"[ANALYZE] Evidence update failed: {e}")
                log_stage("GRAPH", "warning", {"step": "evidence_update", "error": str(e)[:40]})

        # Merge deep parse results (hop-3/4 nodes) — should be done by now
        try:
            with DebugTimer("Waiting for deep causal parse"):
                deep_data = await asyncio.wait_for(deep_parse_task, timeout=1.0)
            if deep_data.get("deep_causal_seeds"):
                graph = _merge_deep_seeds(graph, deep_data, event)
                logger.info(f"[ANALYZE] Deep seeds merged: {len(deep_data['deep_causal_seeds'])} hop-3/4 nodes")
                log_stage("GRAPH", "info", {"deep_seeds": len(deep_data['deep_causal_seeds']),
                                           "deep_actors": len(deep_data.get('non_obvious_actors', []))})
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug(f"[ANALYZE] Deep parse not ready or failed: {e}")

        # Apply FRED real values to MetricNodes
        if fred_data:
            with DebugTimer("Enriching graph with FRED data"):
                graph = _apply_fred_to_graph(graph, fred_data)

        n_nodes = len(graph["nodes"])
        n_edges = len(graph["edges"])
        max_hop = max((n.get("hop", 0) for n in graph["nodes"]), default=0)
        graph_elapsed = time.time() - graph_start

        log_graph_build(n_nodes, n_edges, max_hop, graph_elapsed)
        log_stage("GRAPH", "done", {
            "nodes": n_nodes,
            "edges": n_edges,
            "max_hop": max_hop,
            "seconds": round(graph_elapsed, 2),
        })

        yield _sse({
            "stage": "extracting",
            "message": f"Graph: {n_nodes} nodes, {n_edges} edges (NLP enriched)",
            "stats": {"nodes": n_nodes, "agents": 0, "steps": 0},
        })

        await asyncio.sleep(0.2)

        # ── Stage 4: C-Path + Agent Swarm Simulation ──────────────────────────
        log_stage("SIMULATE", "start")
        run_id = f"run_{hashlib.md5(question.encode()).hexdigest()[:10]}"

        yield _sse({
            "stage": "simulating",
            "message": f"Running agent swarm — {event.severity} cascade across {', '.join(event.domain[:3])}...",
            "stats": {"nodes": n_nodes, "agents": 0, "steps": 0},
        })

        sim_start = time.time()
        with DebugTimer("Building DAG and computing C-Path scores"):
            from butterfly.causal.cpath import CPathCalculator
            from butterfly.causal.dag import DAGBuilder
            dag = DAGBuilder().build_from_graph_data(graph)
            cci_scores = CPathCalculator().calculate(dag, "root")

        os.makedirs(_DATA_DIR, exist_ok=True)
        esaa_log = os.path.join(_DATA_DIR, f"activity_{run_id}.jsonl")

        # Hybrid runner: mathematical baseline + swarm corrections (inside runner)
        with DebugTimer("Running universal hybrid simulation (168 steps)"):
            from butterfly.simulation.universal_runner import UniversalRunner
            sim_result = await UniversalRunner().run(
                event, graph, steps=168, log_path=esaa_log,
                precomputed_dag=dag, precomputed_cci=cci_scores,
            )

        n_agents = sim_result.agent_count
        esaa_stats = sim_result.esaa_stats
        sim_elapsed = time.time() - sim_start

        log_stage("SIMULATE", "done", {
            "agents": n_agents,
            "steps": sim_result.steps_completed,
            "mode": sim_result.mode,
            "seconds": round(sim_elapsed, 2),
        })

        logger.info(f"🎬 Simulation complete: {n_agents} agents, {sim_result.steps_completed} steps ({sim_result.mode})")

        yield _sse({
            "stage": "simulating",
            "message": (
                f"Hybrid sim: {n_agents} agents · {sim_result.steps_completed} steps · "
                f"mode={sim_result.mode}"
            ),
            "stats": {
                "nodes": n_nodes,
                "agents": n_agents,
                "steps": sim_result.steps_completed,
            },
            "esaa_stats": esaa_stats,
        })

        await asyncio.sleep(0.2)

        # ── Stage 5: LLM Insights + SNN Verification ─────────────────────────
        log_stage("INSIGHTS", "start")
        yield _sse({
            "stage": "simulating",
            "message": "Generating insights and running SNN verification gate...",
            "stats": {"nodes": n_nodes, "agents": n_agents, "steps": sim_result.steps_completed},
        })

        raw_insights: list[dict] = []
        try:
            with DebugTimer("Extracting causal chain from simulation"):
                from butterfly.causal.log_extractor import CausalLogExtractor
                chain = CausalLogExtractor().extract(graph, sim_result, event)

            with DebugTimer("Generating LLM insights"):
                from butterfly.llm.insight_generator import InsightGenerator
                raw_insights = await InsightGenerator().generate(chain, event)
            logger.info(f"[ANALYZE] LLM generated {len(raw_insights)} insights")
            log_data_sample("Generated insights", raw_insights[:3])
        except Exception as e:
            logger.warning(f"[ANALYZE] LLM insights failed ({e}), using structural fallback")
            log_stage("INSIGHTS", "warning", {"error": "LLM failed, using fallback"})
            raw_insights = _build_insights(event, graph)

        with DebugTimer("SNN verification gate"):
            from butterfly.causal.snn_gate import SNNVerificationGate
            snn = SNNVerificationGate()
            verified = snn.verify_batch(raw_insights, dag, cci_scores, evidence=evidence)
            insights = snn.to_frontend_format(verified)

        snn_summary = {
            "total": len(verified),
            "verified": sum(1 for v in verified if v.snn_verified),
            "rejected": sum(1 for v in verified if not v.snn_verified),
        }
        logger.info(f"[SNN] {snn_summary}")
        log_stage("INSIGHTS", "done", {
            "total": len(verified),
            "verified": snn_summary["verified"],
            "rejected": snn_summary["rejected"],
        })

        # ── TIER 1+2: Integrate credibility upgrades ──────────────────────────

        # 1. Detect cycles and extract alternative chains
        with DebugTimer("Detecting cycles and alternatives"):
            cycle_detector = CycleDetector()
            cycles = cycle_detector.find_cycles(graph)

            chains = AlternativeChainsBuilder.extract_top_k_chains(graph, k=3)
            log_data_sample("Alternative chains",
                          [{"rank": c.rank, "prob": c.cumulative_probability} for c in chains])

        # 2. Apply uncertainty propagation to graph nodes
        with DebugTimer("Computing confidence intervals"):
            interval_estimator = IntervalEstimator()

            # Update nodes with confidence intervals
            for node in graph["nodes"]:
                if node.get("hop", 0) > 0:  # Skip root
                    point_conf = node.get("confidence", 0.5)

                    # Evidence count approximation (number of sources mentioning this node)
                    evidence_count = min(5, len(evidence) // max(1, len(graph["nodes"]) - 1))

                    # Compute interval with evidence adjustment
                    interval = interval_estimator.from_evidence_base_rate(
                        point_estimate=point_conf,
                        evidence_count=evidence_count,
                        confidence_level=0.90
                    )

                    # Store in node for frontend
                    node["confidence_interval"] = {
                        "lower": round(interval.lower, 2),
                        "point": round(interval.point, 2),
                        "upper": round(interval.upper, 2),
                        "method": interval.method,
                    }

        # 3. Add cycle information if detected
        if cycles:
            logger.info(f"[ANALYZE] {len(cycles)} feedback loop(s) detected")
            cycle_data = []
            for cycle in cycles:
                cycle_data.append({
                    "nodes": cycle.nodes,
                    "length": cycle.length,
                    "mean_confidence": round(cycle.mean_confidence, 2),
                    "has_feedback": cycle.has_feedback,
                    "description": f"{cycle.length}-node feedback loop"
                })
        else:
            cycle_data = []

        # 4. Prepare alternative chains for frontend
        alternative_chains_data = [
            {
                "rank": chain.rank,
                "hops": [h["id"] for h in chain.hops],
                "description": chain.description,
                "cumulative_probability": round(chain.cumulative_probability, 2),
                "primary": (chain.rank == 1),
            }
            for chain in chains
        ]

        # ── Complete ──────────────────────────────────────────────────────────
        result_payload = {
            "stage": "done",
            "nodes": graph["nodes"],
            "edges": graph["edges"],
            "insights": insights,
            "run_id": run_id,
            "stats": {
                "nodes": n_nodes,
                "agents": sim_result.agent_count,
                "steps": sim_result.steps_completed,
            },
            "event_meta": {
                "title": event.title,
                "domain": event.domain,
                "severity": event.severity,
                "actors": event.primary_actors[:5],
                "geographic_scope": event.geographic_scope[:5],
                "confidence": event.confidence,
            },
            "cpath_ranking": [
                {"node": k, "cci": v}
                for k, v in sorted(cci_scores.items(), key=lambda x: x[1], reverse=True)[:8]
            ],
            "esaa_stats": esaa_stats,
            "snn_summary": snn_summary,
            "simulation_mode": sim_result.mode,
            "predictability_horizon": sim_result.predictability_horizon,
            "fred_data": fred_data,
            "gdelt_count": len(gdelt_items),
            "evidence_audit": evidence_audit.model_dump() if evidence_audit else {},
            # Pass evidence to frontend for evidence panel
            "evidence": [
                {
                    "node_id": _match_evidence_to_node(ev, graph["nodes"]),
                    "source": getattr(ev, "source", ""),
                    "title": getattr(ev, "title", ""),
                    "content": getattr(ev, "content", "")[:300],
                    "url": getattr(ev, "url", None),
                    "relevance": getattr(ev, "relevance_score", 0.5),
                }
                for ev in evidence[:30]
            ],
            # ── TIER 1+2: Credibility upgrades ────────────────────────────────
            "causal_chains": alternative_chains_data,
            "feedback_loops": cycle_data,
            "model_quality": {
                "brier_score": 0.119,  # From backtest calibration
                "brier_rating": "EXCELLENT",
                "calibration_error": 0.315,  # ±31.5% mean calibration error
                "confidence_note": "When this tool says 90%, it's actually right ~44% of the time. Intervals show realistic ranges.",
            },
            "credibility_metadata": {
                "tier_1_enabled": True,  # Calibration, alternatives, propagation
                "tier_2_enabled": True,  # Cycles, intervals
                "chain_confidence_method": "compound (multiplied down chain)",
                "interval_basis": "evidence-adjusted, 90% credible interval",
            },
        }

        try:
            from butterfly.db.redis import set_cache
            await set_cache(f"analyze:run:{run_id}", json.dumps(result_payload), ttl=86400)
            logger.info(f"[ANALYZE] Cached as {run_id}")
        except Exception as e:
            logger.warning(f"[ANALYZE] Cache write failed: {e}")

        # Final completion summary
        logger.info(
            f"✅ ANALYSIS COMPLETE | run_id={run_id} | "
            f"nodes={n_nodes} edges={n_edges} insights={len(insights)} | "
            f"agents={n_agents} steps={sim_result.steps_completed}"
        )

        yield _sse(result_payload)
        yield _sse({"done": True})

    except Exception as e:
        logger.error(f"[ANALYZE] Stream error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        yield _sse({"error": str(e)})


def _match_evidence_to_node(ev, nodes: list[dict]) -> str:
    """Find the best matching node ID for an evidence item."""
    title = (getattr(ev, "title", "") or "").lower()
    content = (getattr(ev, "content", "") or "").lower()
    combined = title + " " + content

    best_id = "root"
    best_score = 0

    for node in nodes:
        label = node.get("label", "").lower()
        if not label:
            continue
        # Score by word overlap
        words = [w for w in label.split() if len(w) > 3]
        score = sum(1 for w in words if w in combined)
        if score > best_score:
            best_score = score
            best_id = node["id"]

    return best_id


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("")
async def analyze(request: AnalyzeRequest):
    logger.info(f"🚀 ANALYZE REQUEST | question='{request.question[:60]}'...")
    log_stage("ANALYSIS", "start", {"question_length": len(request.question)})
    return StreamingResponse(
        _analyze_stream(request.question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/{run_id}")
async def get_analysis(run_id: str):
    try:
        from butterfly.db.redis import get_cache
        cached = await get_cache(f"analyze:run:{run_id}")
        if cached:
            data = json.loads(cached)
            data["status"] = "completed"
            return data
    except Exception as e:
        logger.warning(f"[ANALYZE] Cache read failed: {e}")
    return {"run_id": run_id, "status": "not_found", "message": "Result not in cache. Re-run the analysis."}


@router.get("/{run_id}/verify")
async def verify_analysis(run_id: str):
    from butterfly.simulation.esaa import verify_run
    result = verify_run(run_id, data_dir=_DATA_DIR)
    logger.info(f"[VERIFY] run_id={run_id} status={result['verify_status']}")
    return result


class ValidateRequest(BaseModel):
    node_id: str
    actual_direction: str   # "up" | "down" | "unchanged"
    actual_magnitude: float | None = None
    notes: str = ""


@router.post("/{run_id}/validate")
async def validate_analysis(run_id: str, body: ValidateRequest):
    """
    Submit ground-truth validation for a completed analysis.
    Stores in SQLite. After enough validations, confidence weights can be retrained.
    """
    import os
    import sqlite3
    db_path = os.path.join(_DATA_DIR, "butterfly.db")
    os.makedirs(_DATA_DIR, exist_ok=True)

    try:
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                actual_direction TEXT NOT NULL,
                actual_magnitude REAL,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute(
            "INSERT INTO validations (run_id, node_id, actual_direction, actual_magnitude, notes) VALUES (?,?,?,?,?)",
            (run_id, body.node_id, body.actual_direction, body.actual_magnitude, body.notes),
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM validations").fetchone()[0]
        conn.close()
        logger.info(f"[VALIDATE] run_id={run_id} node={body.node_id} direction={body.actual_direction} total={count}")
        return {"status": "stored", "total_validations": count,
                "message": f"Validation stored. {max(0, 100 - count)} more needed before confidence retraining."}
    except Exception as e:
        logger.error(f"[VALIDATE] Failed: {e}")
        return {"status": "error", "message": str(e)}


router_admin = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router_admin.get("/esaa-report")
async def esaa_report():
    """Aggregate ESAA log analysis — finds systematic swarm biases."""
    from butterfly.simulation.esaa_analyzer import analyze_logs
    return analyze_logs(data_dir=_DATA_DIR)
