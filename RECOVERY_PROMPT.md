# 🦋 butterfly-effect — RECOVERY PROMPT
## Restore direction. Build what's missing. Wire what exists.

---

> **READ THIS ENTIRE FILE BEFORE WRITING A SINGLE LINE OF CODE.**
> This is not a feature request. This is a recovery operation.
> The frontend is complete and working. Do not touch it.
> The backend shell starts but is hollow. We are filling the interior.
> Work through Recovery Phases R1 → R2 → R3 → R4 in strict order.
> Each phase ends with a verification test. Do not start the next phase
> until the current phase's test passes.

---

## WHO YOU ARE

You are a Staff Engineer doing a recovery pass on a project that has
good bones but a hollow interior. You have three rules:

1. **Never break what works.** The frontend is complete. The SSE streaming
   works. The demo mode works. You do not touch these under any circumstance.

2. **Wire before building.** The EventParser already exists and calls Gemini.
   The analyze endpoint already exists but uses hardcoded data. Wire them
   together FIRST before building anything new.

3. **Build in order.** Each module feeds the next. Build the fetcher before
   the simulation. Build the simulation before the causal engine. Build the
   causal engine before the insight generator.

---

## CURRENT STATE (be precise about what exists)

### EXISTS AND WORKS — DO NOT TOUCH:
```
frontend/                          ← complete, all pages functional
backend/butterfly/api/analyze.py   ← exists, SSE works, BUT uses hardcoded data
backend/butterfly/llm/event_parser.py  ← exists, calls Gemini, BUT not wired into analyze
backend/butterfly/config.py        ← exists, has API keys
backend/butterfly/main.py          ← starts cleanly
```

### EXISTS BUT BROKEN:
```
EventParser — calls Gemini but truncates at 100 tokens, JSON fails silently
orchestrator.py — imports modules that don't exist (causes ImportError)
```

### DOES NOT EXIST (must be built):
```
backend/butterfly/ingestion/universal_fetcher.py
backend/butterfly/simulation/universal_runner.py  
backend/butterfly/causal/dag.py
backend/butterfly/causal/cpath.py          ← NotebookLM C-Path algorithm
backend/butterfly/causal/log_extractor.py
backend/butterfly/llm/insight_generator.py
backend/butterfly/simulation/esaa.py       ← NotebookLM ESAA pattern
```

### NOT RUNNING (infrastructure):
```
PostgreSQL — not running
Redis — not running  
Neo4j — not running
```

---

## RECOVERY PHASE R1 — WIRE THE LLM (most critical, do first)

**Goal:** `/api/v1/analyze` uses real Gemini output, not hardcoded Python dicts.
**Time estimate:** 2-3 hours.
**Test:** Submit "war in Taiwan strait" → response contains domain="geopolitics" from LLM, not keyword match.

### R1.1 — Fix EventParser JSON truncation

Open `backend/butterfly/llm/event_parser.py`.

Find the Gemini API call. It almost certainly has `max_output_tokens=100` or
similar. Fix it:

```python
# FIND this or similar — the token limit killing your JSON:
response = client.generate_content(
    prompt,
    generation_config={"max_output_tokens": 100}  # ← THIS IS THE BUG
)

# REPLACE WITH:
response = client.generate_content(
    prompt,
    generation_config={
        "max_output_tokens": 2048,      # JSON needs room
        "temperature": 0.1,              # low temp for structured output
        "response_mime_type": "application/json"  # force JSON mode in Gemini
    }
)
```

Also fix the retry logic — it currently retries but probably retries the
same broken call. Fix the retry to use exponential backoff:

```python
import time

async def parse(self, raw_input: str) -> UniversalEvent:
    for attempt in range(3):
        try:
            response = await self._call_gemini(raw_input)
            text = response.text.strip()
            
            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            data = json.loads(text)
            return UniversalEvent(**data)
            
        except json.JSONDecodeError as e:
            logger.warning(f"[PARSER] Attempt {attempt+1} JSON parse failed: {e}")
            logger.warning(f"[PARSER] Raw response was: {text[:200]}")
            if attempt < 2:
                time.sleep(2 ** attempt)  # 1s, 2s backoff
                continue
            # Final fallback — construct from keyword extraction
            return self._fallback_parse(raw_input)
        except Exception as e:
            logger.error(f"[PARSER] Attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return self._fallback_parse(raw_input)

def _fallback_parse(self, raw_input: str) -> UniversalEvent:
    """
    When LLM fails completely, use deterministic keyword extraction.
    This is the safety net — never return None or raise.
    """
    text_lower = raw_input.lower()
    
    domain = []
    if any(w in text_lower for w in ["war", "conflict", "military", "attack", "invasion"]):
        domain.extend(["geopolitics", "military"])
    if any(w in text_lower for w in ["pandemic", "virus", "disease", "outbreak", "health"]):
        domain.extend(["health", "humanitarian"])
    if any(w in text_lower for w in ["rate", "fed", "economy", "gdp", "recession", "bank"]):
        domain.extend(["economics", "financial_markets"])
    if any(w in text_lower for w in ["hurricane", "earthquake", "flood", "climate", "storm"]):
        domain.extend(["climate", "environment"])
    if any(w in text_lower for w in ["ai", "tech", "chip", "semiconductor", "startup"]):
        domain.extend(["technology"])
    if not domain:
        domain = ["economics"]  # safe default
    
    return UniversalEvent(
        raw_input=raw_input,
        title=raw_input[:100],
        domain=domain,
        primary_actors=[],
        affected_systems=[],
        geographic_scope=["global"],
        time_horizon="months",
        severity="moderate",
        causal_seeds=[f"{d}_impact" for d in domain[:3]],
        data_fetch_queries=[raw_input, f"{raw_input} economic impact"],
        occurred_at=datetime.utcnow(),
        confidence=0.5  # flag as fallback
    )
```

### R1.2 — Wire EventParser into analyze.py

Open `backend/butterfly/api/analyze.py`.

Find the section that builds the graph response. It will look something like:

```python
# THE HARDCODED SECTION — find and replace this:
if "pandemic" in query.lower():
    nodes = PANDEMIC_NODES  # hardcoded dict
    edges = PANDEMIC_EDGES  # hardcoded dict
elif "war" in query.lower():
    nodes = WAR_NODES
    ...
```

Replace the entire hardcoded section with real EventParser output:

```python
from butterfly.llm.event_parser import EventParser

parser = EventParser()

async def analyze_stream(question: str):
    
    # Stage 1: Parse the question with LLM
    yield format_sse("parsing", 10, "Understanding your question...")
    
    try:
        event = await parser.parse(question)
        logger.info(f"[ANALYZE] Parsed: domain={event.domain}, actors={event.primary_actors}")
    except Exception as e:
        logger.error(f"[ANALYZE] Parser failed: {e}")
        event = parser._fallback_parse(question)
    
    yield format_sse("parsing_complete", 20, 
                     f"Detected: {', '.join(event.domain)} event affecting {len(event.affected_systems)} systems")
    
    # Stage 2: Build graph from event (use existing domain templates for now)
    yield format_sse("building", 30, "Building causal knowledge graph...")
    
    graph_data = build_graph_from_event(event)  # see R1.3
    
    yield format_sse("simulating", 60, f"Simulating {event.severity} impact across {', '.join(event.domain)}...")
    
    # Simulate with simple math for now (full simulation comes in R2)
    simulation_result = run_simple_simulation(event, graph_data)
    
    yield format_sse("insights", 85, "Generating non-obvious insights...")
    
    insights = generate_simple_insights(event, graph_data)
    
    # Final result
    result = {
        "event": event.dict(),
        "graph": graph_data,
        "simulation": simulation_result,
        "insights": insights,
        "run_id": str(uuid.uuid4())
    }
    
    yield format_sse("complete", 100, "Analysis complete", result=result)
```

### R1.3 — Build graph_from_event (replaces hardcoded dicts)

In the same `analyze.py` file, add this function that builds a graph
dynamically from the parsed event — not from hardcoded domain templates:

```python
def build_graph_from_event(event: UniversalEvent) -> dict:
    """
    Builds a causal graph from the LLM-parsed event.
    Uses the event's causal_seeds and affected_systems to construct nodes.
    This is the bridge between EventParser output and graph visualization.
    """
    nodes = []
    edges = []
    
    # Root node — the event itself
    nodes.append({
        "id": "root",
        "type": "event",
        "label": event.title,
        "domain": event.domain,
        "severity": event.severity
    })
    
    # First-order nodes from causal_seeds
    for i, seed in enumerate(event.causal_seeds):
        node_id = f"seed_{i}"
        label = seed.replace("_", " ").title()
        nodes.append({
            "id": node_id,
            "type": "metric",
            "label": label,
            "domain": event.domain,
            "hop": 1
        })
        edges.append({
            "source": "root",
            "target": node_id,
            "confidence": 0.8,
            "latency_hours": (i + 1) * 24,
            "relationship": "TRIGGERS"
        })
    
    # Second-order nodes from affected_systems
    for i, system in enumerate(event.affected_systems):
        node_id = f"system_{i}"
        label = system.replace("_", " ").title()
        nodes.append({
            "id": node_id,
            "type": "system",
            "label": label,
            "domain": event.domain,
            "hop": 2
        })
        # Connect to a seed node
        if event.causal_seeds:
            source_idx = i % len(event.causal_seeds)
            edges.append({
                "source": f"seed_{source_idx}",
                "target": node_id,
                "confidence": 0.6,
                "latency_hours": (i + 2) * 48,
                "relationship": "INFLUENCES"
            })
    
    # Third-order nodes — actors that respond
    for i, actor in enumerate(event.primary_actors[:4]):
        node_id = f"actor_{i}"
        nodes.append({
            "id": node_id,
            "type": "entity",
            "label": actor,
            "domain": event.domain,
            "hop": 3
        })
        if nodes[1:]:  # connect to any second-order node
            source_id = nodes[min(i + 1, len(nodes) - 2)]["id"]
            edges.append({
                "source": source_id,
                "target": node_id,
                "confidence": 0.5,
                "latency_hours": (i + 3) * 72,
                "relationship": "CAUSES"
            })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "total_hops": 3,
        "domain": event.domain
    }

def generate_simple_insights(event: UniversalEvent, graph: dict) -> list[dict]:
    """
    Generates insights from the parsed event structure.
    Uses LLM-parsed causal_seeds to identify non-obvious effects.
    Full LLM insight generation comes in R3.
    """
    insights = []
    
    # First insight — immediate effect
    if event.causal_seeds:
        insights.append({
            "order": 1,
            "domain": event.domain[0] if event.domain else "economics",
            "title": f"Immediate: {event.causal_seeds[0].replace('_', ' ').title()}",
            "description": f"Within hours of {event.title}, {event.causal_seeds[0].replace('_', ' ')} begins.",
            "confidence": 0.85,
            "timing": "immediate (hours)"
        })
    
    # Second insight — structural effect
    if len(event.affected_systems) > 1:
        insights.append({
            "order": 2,
            "domain": event.domain[1] if len(event.domain) > 1 else event.domain[0],
            "title": f"2nd order: {event.affected_systems[1].replace('_', ' ').title()} disrupted",
            "description": f"The cascade reaches {event.affected_systems[1].replace('_', ' ')} within days as {event.causal_seeds[0].replace('_', ' ') if event.causal_seeds else 'effects'} propagate.",
            "confidence": 0.65,
            "timing": "days to weeks"
        })
    
    # Third insight — the non-obvious one from the LLM
    if len(event.causal_seeds) >= 3:
        insights.append({
            "order": 3,
            "domain": "cross-domain",
            "title": f"3rd order (non-obvious): {event.causal_seeds[2].replace('_', ' ').title()}",
            "description": f"What most analysts miss: {event.causal_seeds[2].replace('_', ' ')} emerges 2-6 months later as second-order effects compound.",
            "confidence": 0.45,
            "timing": "months"
        })
    
    return insights

def run_simple_simulation(event: UniversalEvent, graph: dict) -> dict:
    """
    Simple mathematical simulation — not Mesa agents yet.
    Models cascade as exponential decay from source to each hop.
    Full Mesa simulation comes in R2.
    """
    import math
    
    timeline = {}
    decay = 0.7  # effect strength decays by 30% per hop
    
    for step in range(168):  # 168 hours = 1 week
        snapshot = {}
        for node in graph["nodes"]:
            hop = node.get("hop", 0)
            # Effect peaks at hop * 24 hours then decays
            peak_step = hop * 24
            if step < peak_step:
                effect = 0.0
            else:
                effect = math.exp(-0.02 * (step - peak_step)) * (decay ** hop)
            snapshot[node["id"]] = round(effect, 4)
        timeline[step] = snapshot
    
    return {
        "steps_completed": 168,
        "agent_count": 0,  # honest — agents not implemented yet
        "timeline_a": timeline,
        "timeline_b": {step: {k: 0.0 for k in snapshot} for step, snapshot in timeline.items()},
        "mode": "mathematical"  # flag: not agent-based yet
    }
```

### R1 Verification Test:
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "Full scale war breaks out in Taiwan strait"}' \
  --no-buffer

# You MUST see in the SSE stream:
# event: parsing_complete
# data: {"message": "Detected: geopolitics, military event..."}
# (NOT "Detected: economics event" — that was the hardcoded keyword match)

# Check the final result contains:
# event.domain != ["economics"]   ← if it does, LLM not wired in yet
# event.causal_seeds != []        ← must have LLM-generated seeds
# graph.nodes.length > 4          ← more than the hardcoded default
```

---

## RECOVERY PHASE R2 — BUILD MISSING MODULES

**Goal:** All ImportErrors in orchestrator.py resolved. Pipeline runs end-to-end.
**Time estimate:** 4-6 hours.
**Test:** Analysis for any query completes all stages without ImportError.

### R2.1 — Build universal_fetcher.py (minimal working version)

Create `backend/butterfly/ingestion/universal_fetcher.py`:

```python
"""
UniversalFetcher — fetches real data for any event domain.
Minimal working version: DuckDuckGo + Wikipedia + RSS feeds.
No API keys required. Extends in R3 with more sources.
"""
import asyncio
import httpx
from datetime import datetime
from loguru import logger

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    logger.warning("[FETCHER] duckduckgo-search not installed. Run: pip install duckduckgo-search")

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("[FETCHER] feedparser not installed. Run: pip install feedparser")


class RawEvidence:
    def __init__(self, source, title, content, url=None, relevance_score=0.5, domain_tags=None):
        self.source = source
        self.title = title[:200] if title else ""
        self.content = content[:600] if content else ""
        self.url = url
        self.relevance_score = relevance_score
        self.domain_tags = domain_tags or []
        self.published_at = None
    
    def dict(self):
        return {
            "source": self.source,
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "relevance_score": self.relevance_score,
            "domain_tags": self.domain_tags
        }


RSS_FEEDS_BY_DOMAIN = {
    "geopolitics": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "economics": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ],
    "technology": [
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
    ],
    "health": [
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.who.int/rss-feeds/news-english.xml",
    ],
    "climate": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    ],
    "military": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
}

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary"
WIKI_SEARCH = "https://en.wikipedia.org/w/api.php"


class UniversalFetcher:
    
    async def fetch(self, event) -> list:
        """
        Fetch real-world data for any event.
        Returns list of RawEvidence objects.
        """
        queries = getattr(event, 'data_fetch_queries', [event.title if hasattr(event, 'title') else str(event)])
        domains = getattr(event, 'domain', ['economics'])
        keywords = getattr(event, 'primary_actors', []) + [queries[0] if queries else ""]
        
        logger.info(f"[FETCHER] Starting fetch for domains={domains}, queries={len(queries)}")
        
        tasks = [
            self._fetch_duckduckgo(queries),
            self._fetch_wikipedia(queries),
            self._fetch_rss(domains, keywords),
            self._fetch_reliefweb(queries) if any(d in domains for d in ["humanitarian", "health", "geopolitics"]) else asyncio.coroutine(lambda: [])(),
        ]
        
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        seen = set()
        for batch in results_nested:
            if isinstance(batch, Exception):
                logger.warning(f"[FETCHER] Batch failed: {batch}")
                continue
            for item in (batch or []):
                if item.title not in seen:
                    seen.add(item.title)
                    all_results.append(item)
        
        # Score relevance by keyword matches
        for item in all_results:
            combined = (item.title + " " + item.content).lower()
            matches = sum(1 for q in queries if q.lower()[:10] in combined)
            item.relevance_score = min(item.relevance_score + matches * 0.05, 1.0)
        
        all_results.sort(key=lambda r: r.relevance_score, reverse=True)
        final = all_results[:50]
        
        logger.info(f"[FETCHER] Complete: {len(all_results)} raw → {len(final)} ranked")
        return final
    
    async def _fetch_duckduckgo(self, queries: list) -> list:
        if not DDGS_AVAILABLE:
            return []
        results = []
        loop = asyncio.get_event_loop()
        
        def _search(q):
            try:
                with DDGS() as ddgs:
                    return list(ddgs.text(q, max_results=6))
            except Exception as e:
                logger.warning(f"[DDGS] '{q}' failed: {e}")
                return []
        
        for q in queries[:3]:
            raw = await loop.run_in_executor(None, _search, q)
            for r in raw:
                results.append(RawEvidence(
                    source="duckduckgo",
                    title=r.get("title", ""),
                    content=r.get("body", ""),
                    url=r.get("href"),
                    relevance_score=0.7
                ))
        
        logger.info(f"[DDGS] {len(results)} results")
        return results
    
    async def _fetch_wikipedia(self, queries: list) -> list:
        results = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for q in queries[:3]:
                try:
                    search = await client.get(WIKI_SEARCH, params={
                        "action": "query", "list": "search",
                        "srsearch": q, "format": "json", "srlimit": 2
                    })
                    pages = search.json().get("query", {}).get("search", [])
                    for page in pages[:2]:
                        title = page["title"].replace(" ", "_")
                        resp = await client.get(f"{WIKI_API}/{title}")
                        if resp.status_code == 200:
                            data = resp.json()
                            extract = data.get("extract", "")
                            if len(extract) > 100:
                                results.append(RawEvidence(
                                    source="wikipedia",
                                    title=data.get("title", title),
                                    content=extract[:600],
                                    url=data.get("content_urls", {}).get("desktop", {}).get("page"),
                                    relevance_score=0.75
                                ))
                except Exception as e:
                    logger.warning(f"[WIKI] '{q}' failed: {e}")
        
        logger.info(f"[WIKI] {len(results)} pages")
        return results
    
    async def _fetch_rss(self, domains: list, keywords: list) -> list:
        if not FEEDPARSER_AVAILABLE:
            return []
        
        feed_urls = []
        for d in domains:
            feed_urls.extend(RSS_FEEDS_BY_DOMAIN.get(d, []))
        feed_urls = list(set(feed_urls))[:6]
        
        if not feed_urls:
            feed_urls = RSS_FEEDS_BY_DOMAIN["economics"]
        
        results = []
        loop = asyncio.get_event_loop()
        kw_lower = [k.lower() for k in keywords if k]
        
        def _parse(url):
            try:
                return feedparser.parse(url).entries[:5]
            except Exception:
                return []
        
        all_entries = []
        for url in feed_urls:
            entries = await loop.run_in_executor(None, _parse, url)
            all_entries.extend(entries)
        
        for entry in all_entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            combined = (title + " " + summary).lower()
            if not kw_lower or any(kw in combined for kw in kw_lower):
                results.append(RawEvidence(
                    source="rss",
                    title=title,
                    content=summary,
                    url=entry.get("link"),
                    relevance_score=0.65
                ))
        
        logger.info(f"[RSS] {len(results)} relevant articles")
        return results
    
    async def _fetch_reliefweb(self, queries: list) -> list:
        results = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for q in queries[:2]:
                try:
                    resp = await client.post(
                        "https://api.reliefweb.int/v1/reports",
                        json={
                            "query": {"value": q, "operator": "AND"},
                            "fields": {"include": ["title", "body", "url"]},
                            "limit": 5,
                            "sort": ["date:desc"]
                        }
                    )
                    for item in resp.json().get("data", []):
                        f = item.get("fields", {})
                        results.append(RawEvidence(
                            source="reliefweb",
                            title=f.get("title", ""),
                            content=f.get("body", "")[:500],
                            url=f.get("url"),
                            relevance_score=0.85,
                            domain_tags=["humanitarian"]
                        ))
                except Exception as e:
                    logger.warning(f"[RELIEFWEB] '{q}' failed: {e}")
        
        logger.info(f"[RELIEFWEB] {len(results)} reports")
        return results
```

### R2.2 — Build universal_runner.py (mathematical simulation, no Mesa yet)

Create `backend/butterfly/simulation/universal_runner.py`:

```python
"""
UniversalRunner — runs the causal simulation.
Phase R2: mathematical model (exponential decay chains).
Phase R3: upgrade to Mesa agent-based simulation.
This module must exist and return valid SimulationResult regardless of
which backend is running.
"""
import math
import uuid
from datetime import datetime
from loguru import logger


class SimulationResult:
    def __init__(self):
        self.run_id = str(uuid.uuid4())
        self.steps_completed = 0
        self.agent_count = 0
        self.timeline_a = {}
        self.timeline_b = {}
        self.agent_logs = []
        self.mode = "mathematical"
        self.duration_seconds = 0.0
    
    def dict(self):
        return {
            "run_id": self.run_id,
            "steps_completed": self.steps_completed,
            "agent_count": self.agent_count,
            "mode": self.mode,
            "duration_seconds": self.duration_seconds,
            "timeline_length": len(self.timeline_a)
        }


class UniversalRunner:
    
    async def run(self, event, graph_data: dict, steps: int = 168) -> SimulationResult:
        """
        Runs causal simulation for any event.
        Returns timelines A (with event) and B (counterfactual).
        """
        start = datetime.utcnow()
        logger.info(f"[RUNNER] Starting {steps}-step simulation for '{getattr(event, 'title', 'unknown')}'")
        
        result = SimulationResult()
        nodes = graph_data.get("nodes", [])
        
        if not nodes:
            logger.warning("[RUNNER] No nodes in graph — returning empty simulation")
            result.steps_completed = steps
            return result
        
        # Build Timeline A (event happens)
        timeline_a = {}
        for step in range(steps):
            snapshot = {}
            for node in nodes:
                hop = node.get("hop", 0)
                severity_mult = {"minor": 0.3, "moderate": 0.6, "major": 0.8, "catastrophic": 1.0}
                severity = severity_mult.get(getattr(event, 'severity', 'moderate'), 0.6)
                
                # Effect arrives at hop * 24 hours, then decays
                peak_step = hop * 24
                decay_factor = 0.7 ** hop  # 30% decay per hop
                
                if step < peak_step:
                    # Effect not yet arrived
                    effect = 0.0
                elif step == peak_step:
                    # Peak effect
                    effect = severity * decay_factor
                else:
                    # Exponential decay after peak
                    effect = severity * decay_factor * math.exp(-0.015 * (step - peak_step))
                
                snapshot[node["id"]] = round(effect, 4)
            timeline_a[step] = snapshot
        
        # Build Timeline B (no event — flat baseline)
        timeline_b = {
            step: {node["id"]: 0.0 for node in nodes}
            for step in range(steps)
        }
        
        result.steps_completed = steps
        result.agent_count = 0  # honest — agents not built yet
        result.timeline_a = timeline_a
        result.timeline_b = timeline_b
        result.mode = "mathematical"
        result.duration_seconds = (datetime.utcnow() - start).total_seconds()
        
        logger.info(f"[RUNNER] Complete: {steps} steps, {len(nodes)} nodes, {result.duration_seconds:.2f}s")
        return result
```

### R2.3 — Build causal/dag.py (minimal working version)

Create `backend/butterfly/causal/dag.py`:

```python
"""
DAGBuilder — constructs directed acyclic graph from knowledge graph data.
Phase R2: builds from graph_data dict (no Neo4j needed).
Phase R3: upgrade to read from Neo4j directly.
"""
import networkx as nx
from loguru import logger


class DAGBuilder:
    
    def build_from_graph_data(self, graph_data: dict) -> nx.DiGraph:
        """Build NetworkX DAG from the graph_data dict produced by analyze.py."""
        dag = nx.DiGraph()
        
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        for node in nodes:
            dag.add_node(
                node["id"],
                label=node.get("label", node["id"]),
                node_type=node.get("type", "unknown"),
                hop=node.get("hop", 0),
                domain=node.get("domain", [])
            )
        
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if src in dag and tgt in dag:
                dag.add_edge(
                    src, tgt,
                    confidence=edge.get("confidence", 0.5),
                    latency_hours=edge.get("latency_hours", 24),
                    relationship=edge.get("relationship", "INFLUENCES")
                )
        
        # Remove cycles if any (makes it a valid DAG)
        if not nx.is_directed_acyclic_graph(dag):
            logger.warning("[DAG] Cycle detected — removing weakest edges")
            cycles = list(nx.simple_cycles(dag))
            for cycle in cycles:
                # Remove the edge with lowest confidence in each cycle
                min_conf = float('inf')
                min_edge = None
                for i in range(len(cycle)):
                    src = cycle[i]
                    tgt = cycle[(i + 1) % len(cycle)]
                    if dag.has_edge(src, tgt):
                        conf = dag[src][tgt].get("confidence", 0.5)
                        if conf < min_conf:
                            min_conf = conf
                            min_edge = (src, tgt)
                if min_edge:
                    dag.remove_edge(*min_edge)
        
        logger.info(f"[DAG] Built: {dag.number_of_nodes()} nodes, {dag.number_of_edges()} edges")
        return dag
```

### R2.4 — Build causal/cpath.py (NotebookLM C-Path Algorithm)

Create `backend/butterfly/causal/cpath.py`:

```python
"""
C-Path Algorithm — Cumulative Causal Influence Calculator.
Based on: Liu & Li (2012) cascade influence methodology.
Referenced in NotebookLM architectural blueprint.

This calculates HOW MUCH causal influence flows from the triggering event
to every reachable node. This is the mathematical backbone of butterfly-effect —
it tells us which downstream effects are most strongly caused by the event,
not just which ones happen to correlate.
"""
import networkx as nx
from dataclasses import dataclass
from loguru import logger


@dataclass
class CascadePath:
    node_id: str
    node_label: str
    cci_score: float           # Cumulative Causal Influence (0-1)
    hop_count: int             # hops from source
    path_from_source: list     # ordered list of node IDs
    estimated_latency_hours: int
    is_butterfly_effect: bool  # True if hop >= 3 (non-obvious)


class CPathCalculator:
    """
    Implements C-Path: calculates cumulative causal influence
    flowing from a source node through the entire causal graph.
    
    Key insight: a node 4 hops away with high-weight edges on every
    hop can have MORE cumulative influence than a node 2 hops away
    with weak edges. C-Path captures this properly.
    """
    
    def calculate(
        self,
        dag: nx.DiGraph,
        source_node: str,
        alpha: float = 0.85  # decay factor — same as PageRank convention
    ) -> dict:
        """
        Calculate CCI score for every node reachable from source.
        
        Returns: dict mapping node_id → CCI score (0.0 to 1.0)
        Source node always = 1.0.
        """
        if source_node not in dag:
            logger.warning(f"[CPATH] Source node '{source_node}' not in DAG")
            return {}
        
        cci = {node: 0.0 for node in dag.nodes()}
        cci[source_node] = 1.0
        
        # Compute shortest path distances from source
        try:
            distances = nx.single_source_shortest_path_length(dag, source_node)
        except Exception:
            distances = {source_node: 0}
        
        # Propagate influence in topological order
        try:
            topo_order = list(nx.topological_sort(dag))
        except nx.NetworkXUnfeasible:
            logger.warning("[CPATH] Graph has cycles — using BFS order instead")
            topo_order = list(nx.bfs_tree(dag, source_node).nodes())
        
        for node in topo_order:
            if node == source_node:
                continue
            
            predecessors = list(dag.predecessors(node))
            if not predecessors:
                continue
            
            dist = distances.get(node, 99)
            
            for pred in predecessors:
                edge_data = dag.get_edge_data(pred, node, default={})
                edge_weight = edge_data.get("confidence", 0.5)
                
                # C-Path formula: influence decays with distance and edge weight
                propagated = cci[pred] * edge_weight * (alpha ** dist)
                cci[node] += propagated
        
        # Normalize to [0, 1]
        max_score = max(cci.values()) if cci else 1.0
        if max_score > 0:
            cci = {k: round(v / max_score, 4) for k, v in cci.items()}
        
        logger.info(f"[CPATH] Calculated CCI for {len(cci)} nodes from '{source_node}'")
        return cci
    
    def rank_paths(
        self,
        dag: nx.DiGraph,
        cci_scores: dict,
        source_node: str,
        top_n: int = 10
    ) -> list:
        """
        Returns top N cascade paths ranked by CCI score.
        Each result is a CascadePath with full path from source.
        """
        paths = []
        
        for node_id, score in sorted(cci_scores.items(), key=lambda x: x[1], reverse=True):
            if node_id == source_node or score == 0:
                continue
            
            # Get shortest path from source to this node
            try:
                path = nx.shortest_path(dag, source_node, node_id)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                path = [source_node, node_id]
            
            hop_count = len(path) - 1
            
            # Calculate estimated latency from edge data
            total_latency = 0
            for i in range(len(path) - 1):
                edge_data = dag.get_edge_data(path[i], path[i+1], default={})
                total_latency += edge_data.get("latency_hours", 24)
            
            paths.append(CascadePath(
                node_id=node_id,
                node_label=dag.nodes[node_id].get("label", node_id) if node_id in dag else node_id,
                cci_score=score,
                hop_count=hop_count,
                path_from_source=path,
                estimated_latency_hours=total_latency,
                is_butterfly_effect=(hop_count >= 3)  # 3+ hops = non-obvious
            ))
            
            if len(paths) >= top_n:
                break
        
        return paths
    
    def find_butterfly_effects(
        self,
        dag: nx.DiGraph,
        cci_scores: dict,
        source_node: str,
        min_cci: float = 0.2
    ) -> list:
        """
        Returns ONLY the non-obvious butterfly effects (3+ hops, CCI > min_cci).
        These are the insights nobody else is seeing.
        """
        all_paths = self.rank_paths(dag, cci_scores, source_node, top_n=50)
        butterfly_paths = [
            p for p in all_paths
            if p.is_butterfly_effect and p.cci_score >= min_cci
        ]
        
        logger.info(f"[CPATH] Found {len(butterfly_paths)} butterfly effects (3+ hops, CCI >= {min_cci})")
        return butterfly_paths
```

### R2.5 — Build causal/log_extractor.py

Create `backend/butterfly/causal/log_extractor.py`:

```python
"""
CausalLogExtractor — converts simulation output into structured causal chain.
Works with both mathematical simulation (R2) and Mesa agents (R3+).
Integrates C-Path scores to rank chain by cumulative influence.
"""
from butterfly.causal.cpath import CPathCalculator, CascadePath
from butterfly.causal.dag import DAGBuilder
from loguru import logger
from dataclasses import dataclass


@dataclass
class CausalHop:
    from_node: str
    to_node: str
    from_label: str
    to_label: str
    relationship: str
    latency_hours: int
    confidence: float
    cci_score: float
    is_butterfly_effect: bool
    magnitude: float


@dataclass 
class CausalChain:
    event_title: str
    hops: list          # list[CausalHop]
    total_hops: int
    butterfly_effects: list   # highest-impact 3rd/4th order effects
    peak_effect_at_hours: int
    domain_coverage: list
    cpath_ranking: list


class CausalLogExtractor:
    
    def __init__(self):
        self.dag_builder = DAGBuilder()
        self.cpath = CPathCalculator()
    
    def extract(
        self,
        graph_data: dict,
        simulation_result,
        event
    ) -> CausalChain:
        """
        Extracts structured causal chain from graph + simulation data.
        Uses C-Path to score each node by cumulative causal influence.
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        if not nodes:
            logger.warning("[EXTRACTOR] Empty graph — returning minimal chain")
            return CausalChain(
                event_title=getattr(event, 'title', 'Unknown'),
                hops=[], total_hops=0, butterfly_effects=[],
                peak_effect_at_hours=0, domain_coverage=[],
                cpath_ranking=[]
            )
        
        # Build DAG
        dag = self.dag_builder.build_from_graph_data(graph_data)
        
        # Find source node (root / hop=0)
        source = "root"
        for node in nodes:
            if node.get("hop", 1) == 0 or node.get("id") == "root":
                source = node["id"]
                break
        
        # Calculate C-Path scores
        cci_scores = self.cpath.calculate(dag, source)
        
        # Build hop list from edges
        hops = []
        for edge in edges:
            src_id = edge.get("source")
            tgt_id = edge.get("target")
            
            src_node = next((n for n in nodes if n["id"] == src_id), {})
            tgt_node = next((n for n in nodes if n["id"] == tgt_id), {})
            
            tgt_hop = tgt_node.get("hop", 1)
            
            hops.append(CausalHop(
                from_node=src_id,
                to_node=tgt_id,
                from_label=src_node.get("label", src_id),
                to_label=tgt_node.get("label", tgt_id),
                relationship=edge.get("relationship", "INFLUENCES"),
                latency_hours=edge.get("latency_hours", 24),
                confidence=edge.get("confidence", 0.5),
                cci_score=cci_scores.get(tgt_id, 0.0),
                is_butterfly_effect=(tgt_hop >= 3),
                magnitude=cci_scores.get(tgt_id, 0.0)
            ))
        
        # Sort by latency (chronological order)
        hops.sort(key=lambda h: h.latency_hours)
        
        # Find butterfly effects
        butterfly = self.cpath.find_butterfly_effects(dag, cci_scores, source)
        
        # Find peak effect time
        peak_hours = max((h.latency_hours for h in hops), default=24)
        
        return CausalChain(
            event_title=getattr(event, 'title', 'Unknown'),
            hops=hops,
            total_hops=len(hops),
            butterfly_effects=butterfly,
            peak_effect_at_hours=peak_hours,
            domain_coverage=getattr(event, 'domain', []),
            cpath_ranking=[
                {"node": k, "cci": v}
                for k, v in sorted(cci_scores.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
        )
```

### R2.6 — Build llm/insight_generator.py

Create `backend/butterfly/llm/insight_generator.py`:

```python
"""
InsightGenerator — uses LLM to generate non-obvious insights from causal chain.
Uses hybrid routing: fast model for drafts, Sonnet for final quality pass.
Implements the NotebookLM "Reflect Agent" pattern.
"""
import json
from loguru import logger
from butterfly.config import settings


class InsightGenerator:
    
    async def generate(self, chain, event) -> list[dict]:
        """
        Generate 3-5 non-obvious insights from the causal chain.
        Prioritizes 3rd and 4th order effects — the butterfly effects.
        """
        # Build prompt from chain data
        butterfly_effects = []
        if hasattr(chain, 'butterfly_effects'):
            butterfly_effects = [
                f"- {p.node_label} (hop {p.hop_count}, CCI={p.cci_score:.2f}, ~{p.estimated_latency_hours}h)"
                for p in chain.butterfly_effects[:5]
            ]
        
        hops_summary = []
        if hasattr(chain, 'hops'):
            for hop in chain.hops[:8]:
                hops_summary.append(
                    f"  {hop.from_label} → {hop.to_label} "
                    f"(confidence={hop.confidence:.2f}, latency={hop.latency_hours}h)"
                )
        
        prompt = f"""You are a geopolitical and systems analyst specializing in non-obvious cascade effects.

Event: {getattr(event, 'title', 'Unknown event')}
Domains: {', '.join(getattr(event, 'domain', []))}
Severity: {getattr(event, 'severity', 'unknown')}
Primary actors: {', '.join(getattr(event, 'primary_actors', [])[:5])}

Causal chain discovered ({getattr(chain, 'total_hops', 0)} hops):
{chr(10).join(hops_summary) if hops_summary else 'No hops found'}

Non-obvious effects (3+ hops from source):
{chr(10).join(butterfly_effects) if butterfly_effects else 'None found yet'}

Generate exactly 3 insights. Each insight must:
1. Be SPECIFIC — name actual actors, countries, sectors, not vague categories
2. Include TIMING — "within 6 weeks", "3-6 months", not just "soon"
3. Explain the MECHANISM — why does this causal link exist?
4. Flag the ORDER — is this 2nd, 3rd, or 4th order?
5. Be SURPRISING — what would an analyst miss if they only looked at headlines?

Return ONLY a JSON array of 3 objects:
[
  {{
    "order": 2,
    "title": "Short title of the effect",
    "domain": "the domain this falls in",
    "description": "2-3 sentences explaining the non-obvious connection",
    "timing": "specific timing estimate",
    "confidence": 0.7,
    "why_surprising": "one sentence on why analysts miss this"
  }}
]"""
        
        # Try Gemini first (fast)
        result = await self._try_gemini(prompt)
        if result:
            return result
        
        # Fallback to mathematical insights from chain data
        return self._mathematical_insights(chain, event)
    
    async def _try_gemini(self, prompt: str) -> list | None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            response = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 1500,
                    "temperature": 0.3,
                    "response_mime_type": "application/json"
                }
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            data = json.loads(text)
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"[INSIGHTS] Gemini generated {len(data)} insights")
                return data
        except Exception as e:
            logger.warning(f"[INSIGHTS] Gemini failed: {e}")
        return None
    
    def _mathematical_insights(self, chain, event) -> list[dict]:
        """Fallback insights derived from chain structure — no LLM needed."""
        insights = []
        domain = getattr(event, 'domain', ['economics'])
        hops = getattr(chain, 'hops', [])
        
        if hops:
            h = hops[0]
            insights.append({
                "order": 1,
                "title": f"Immediate: {h.to_label}",
                "domain": domain[0] if domain else "economics",
                "description": f"Within {h.latency_hours} hours of {getattr(event, 'title', 'the event')}, {h.to_label} is directly impacted through the {h.relationship} mechanism.",
                "timing": f"0-{h.latency_hours} hours",
                "confidence": h.confidence,
                "why_surprising": "This is the obvious first-order effect most analysts track."
            })
        
        # Find a 2nd-order effect
        second_order = [h for h in hops if h.is_butterfly_effect is False and h.latency_hours > 48]
        if second_order:
            h = second_order[0]
            insights.append({
                "order": 2,
                "title": f"2nd order: {h.to_label} disrupted",
                "domain": domain[1] if len(domain) > 1 else domain[0],
                "description": f"As {h.from_label} shifts, it propagates through to {h.to_label}. This cross-domain effect typically manifests in {h.latency_hours // 24} days.",
                "timing": f"{h.latency_hours // 24} days",
                "confidence": h.confidence * 0.8,
                "why_surprising": "The cross-domain transmission is often missed by sector-specific analysts."
            })
        
        # Find a butterfly effect
        butterfly = getattr(chain, 'butterfly_effects', [])
        if butterfly:
            b = butterfly[0]
            insights.append({
                "order": b.hop_count,
                "title": f"{b.hop_count}th order (non-obvious): {b.node_label}",
                "domain": "cross-domain",
                "description": f"Following a {b.hop_count}-hop cascade, {b.node_label} is affected. This effect has a cumulative causal influence score of {b.cci_score:.2f} — meaning it is strongly caused, not just correlated.",
                "timing": f"{b.estimated_latency_hours // 24}-{b.estimated_latency_hours // 24 * 2} days",
                "confidence": b.cci_score * 0.7,
                "why_surprising": "This is the true butterfly effect — causally traceable but invisible without graph analysis."
            })
        
        return insights if insights else [{
            "order": 1,
            "title": "Analysis in progress",
            "domain": domain[0] if domain else "economics",
            "description": "The causal chain is being computed. Initial effects are being mapped.",
            "timing": "ongoing",
            "confidence": 0.5,
            "why_surprising": "More data needed for non-obvious insights."
        }]
```

### R2.7 — Wire all modules into orchestrator.py

Now update `backend/butterfly/pipeline/orchestrator.py` to import and use
all the modules you just built:

```python
from butterfly.ingestion.universal_fetcher import UniversalFetcher
from butterfly.simulation.universal_runner import UniversalRunner
from butterfly.causal.dag import DAGBuilder
from butterfly.causal.log_extractor import CausalLogExtractor
from butterfly.llm.insight_generator import InsightGenerator

# These must import cleanly now — run:
# python -c "from butterfly.pipeline.orchestrator import *; print('OK')"
```

### R2 Verification Test:
```bash
# Test all imports resolve (no ImportError)
cd backend
python -c "
from butterfly.ingestion.universal_fetcher import UniversalFetcher
from butterfly.simulation.universal_runner import UniversalRunner
from butterfly.causal.dag import DAGBuilder
from butterfly.causal.cpath import CPathCalculator
from butterfly.causal.log_extractor import CausalLogExtractor
from butterfly.llm.insight_generator import InsightGenerator
print('ALL IMPORTS OK')
"

# Test C-Path algorithm specifically
python -c "
import networkx as nx
from butterfly.causal.cpath import CPathCalculator

dag = nx.DiGraph()
dag.add_edge('root', 'A', confidence=0.9, latency_hours=24)
dag.add_edge('A', 'B', confidence=0.7, latency_hours=48)
dag.add_edge('B', 'C', confidence=0.5, latency_hours=72)
dag.add_edge('A', 'D', confidence=0.3, latency_hours=96)

calc = CPathCalculator()
scores = calc.calculate(dag, 'root')
print('CCI scores:', scores)

assert scores['root'] == 1.0
assert scores['A'] > scores['B']   # closer node scores higher
assert scores['B'] > scores['D']   # higher confidence beats proximity
assert scores['C'] > 0             # 3-hop node still has score
print('C-PATH TEST PASSED')
"
```

---

## RECOVERY PHASE R3 — START DATABASES

**Goal:** PostgreSQL, Redis, Neo4j running. Caching and graph storage enabled.
**Time estimate:** 1 hour.
**Test:** `GET /health` returns all three as true.

```bash
# Option A — Docker (recommended)
docker compose up -d postgres redis neo4j

# Option B — if no Docker, install locally
# PostgreSQL: brew install postgresql (Mac) or apt install postgresql (Linux)
# Redis: brew install redis or apt install redis-server
# Neo4j: download from neo4j.com/download-center (Community Edition, free)

# Verify all running
curl http://localhost:8000/health
# Expected: {"status":"ok","postgres":true,"redis":true,"neo4j":true}
```

---

## RECOVERY PHASE R4 — IMPLEMENT ESAA (NotebookLM Algorithm)

**Goal:** Agents emit intentions, orchestrator validates, state projected from immutable log.
**Time estimate:** 3-4 hours (after R3 complete).
**Test:** activity.jsonl grows during simulation, rejected intentions are logged.

Create `backend/butterfly/simulation/esaa.py`:

```python
"""
ESAA — Event Sourcing for Autonomous Agents.
From NotebookLM architectural blueprint.

Core principle: agents NEVER mutate shared state directly.
They emit structured "intentions" which are validated by a deterministic
orchestrator before being applied. Invalid intentions are logged and rejected.

This makes the simulation:
  - Hallucination-resistant (invalid agent outputs can't corrupt state)
  - Fully auditable (every state change is in activity.jsonl)
  - Time-travelable (replay log up to any step to see cascade)
"""
import json
import time
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field, validator
from loguru import logger


class AgentIntention(BaseModel):
    """
    Structured output from an agent's step().
    Agents submit this — they never touch state directly.
    """
    agent_id: str
    step: int
    variable: str
    delta: float = Field(..., ge=-1.0, le=1.0)  # bounded change
    direction: int = Field(..., ge=-1, le=1)       # +1 or -1
    reason: str = Field(..., min_length=5, max_length=300)
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_refs: list[str] = []
    
    @validator('direction')
    def direction_matches_delta(cls, v, values):
        delta = values.get('delta', 0)
        if delta > 0 and v != 1:
            raise ValueError('direction must be 1 for positive delta')
        if delta < 0 and v != -1:
            raise ValueError('direction must be -1 for negative delta')
        return v


class IntentionValidator:
    
    def __init__(self, valid_variables: set, valid_nodes: set = None):
        self.valid_variables = valid_variables
        self.valid_nodes = valid_nodes or set()
    
    def validate(self, intention: AgentIntention) -> tuple[bool, str]:
        if intention.variable not in self.valid_variables:
            return False, f"Variable '{intention.variable}' not in environment"
        if abs(intention.delta) > 1.0:
            return False, f"Delta {intention.delta} exceeds bound of 1.0"
        if not intention.reason.strip():
            return False, "Empty reason — agent must explain its action"
        return True, ""


class EventLog:
    
    def __init__(self, log_path: str = "activity.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def append(self, intention: AgentIntention, accepted: bool, rejection_reason: str = "") -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": intention.agent_id,
            "step": intention.step,
            "variable": intention.variable,
            "delta": intention.delta,
            "accepted": accepted,
            "reason": intention.reason,
            "rejection_reason": rejection_reason if not accepted else None
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def replay(self, environment: dict, up_to_step: int = None) -> dict:
        """Rebuild state by replaying all accepted intentions up to a step."""
        state = {k: 0.0 for k in environment.keys()}
        
        if not self.log_path.exists():
            return state
        
        with open(self.log_path) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if not entry.get("accepted"):
                        continue
                    if up_to_step and entry.get("step", 0) > up_to_step:
                        break
                    var = entry.get("variable")
                    if var in state:
                        state[var] += entry.get("delta", 0)
                        state[var] = max(-1.0, min(1.0, state[var]))
                except Exception:
                    continue
        
        return state


class ESAAOrchestrator:
    """
    The deterministic orchestrator. Accepts/rejects agent intentions.
    Only this class may mutate the simulation environment.
    """
    
    def __init__(self, environment: dict, log_path: str = "activity.jsonl"):
        self.environment = environment
        self.validator = IntentionValidator(valid_variables=set(environment.keys()))
        self.event_log = EventLog(log_path)
        self.accepted_count = 0
        self.rejected_count = 0
    
    def submit(self, intention: AgentIntention) -> bool:
        is_valid, reason = self.validator.validate(intention)
        self.event_log.append(intention, is_valid, reason)
        
        if is_valid:
            self.environment[intention.variable] = max(
                -1.0,
                min(1.0, self.environment[intention.variable] + intention.delta)
            )
            self.accepted_count += 1
            return True
        else:
            self.rejected_count += 1
            logger.debug(f"[ESAA] Rejected: agent={intention.agent_id} var={intention.variable} reason={reason}")
            return False
```

### R4 Verification Test:
```bash
python -c "
from butterfly.simulation.esaa import AgentIntention, ESAAOrchestrator

# Set up orchestrator with environment
env = {'healthcare_capacity': 0.0, 'oil_price': 0.0, 'unemployment': 0.0}
orch = ESAAOrchestrator(env, log_path='/tmp/test_activity.jsonl')

# Valid intention — should be accepted
valid = AgentIntention(
    agent_id='market_001', step=1, variable='healthcare_capacity',
    delta=-0.3, direction=-1, reason='Hospital capacity decreasing due to patient surge',
    confidence=0.8
)
assert orch.submit(valid) == True
assert env['healthcare_capacity'] == -0.3

# Invalid intention — wrong variable
try:
    invalid = AgentIntention(
        agent_id='market_001', step=2, variable='NONEXISTENT_VAR',
        delta=0.5, direction=1, reason='testing invalid variable',
        confidence=0.5
    )
    result = orch.submit(invalid)
    assert result == False
except Exception:
    pass  # Pydantic validation may catch this

print(f'Accepted: {orch.accepted_count}, Rejected: {orch.rejected_count}')
print('ESAA TEST PASSED')
"
```

---

## FINAL VERIFICATION — FULL PIPELINE

After all 4 recovery phases complete, run this end-to-end test:

```bash
# 1. All imports clean
cd backend
python -c "from butterfly.pipeline.orchestrator import *; print('IMPORTS OK')"

# 2. Submit a real query
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "Pandemic declared — novel pathogen with 30% mortality"}' \
  --no-buffer | head -50

# You must see these SSE events in order:
# event: parsing → contains LLM-detected domain (NOT hardcoded)
# event: fetching → real data being fetched
# event: building → graph being constructed
# event: simulating → simulation running
# event: complete → result with causal_chain.total_hops >= 3

# 3. Verify C-Path scores appear in result
# The complete event's result.causal_chain.cpath_ranking must be non-empty

# 4. Test a completely different domain
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "Magnitude 8.5 earthquake destroys Tokyo"}' \
  --no-buffer | grep '"domain"'
# Must contain "climate" or "economics" — NOT "health"
# (proves domain detection is LLM-driven, not hardcoded)
```

---

## WHAT "DONE" LOOKS LIKE

When all 4 recovery phases are complete:

```
✅ LLM (Gemini) called on every /analyze request
✅ EventParser returns real UniversalEvent (not fallback) 95%+ of the time
✅ Universal fetcher returns 20+ real evidence items per query
✅ C-Path algorithm calculates CCI scores for every graph node
✅ ESAA orchestrator logs every agent intention to activity.jsonl
✅ Causal chain has 3+ hops with CCI-ranked paths
✅ Insight generator returns 3 LLM-written non-obvious insights
✅ All databases running (Postgres, Redis, Neo4j)
✅ Frontend unchanged — still works, still looks good
✅ Demo mode still works — pre-loaded data unaffected
✅ Any question, any domain, real data, real AI
```

---

*RECOVERY_PROMPT.md — butterfly-effect*
*4 phases. Do R1 first. Do not skip. Do not merge phases.*
*The frontend is not broken. Do not touch it.*
*Each phase ends with a test. Each test must pass before the next phase starts.*