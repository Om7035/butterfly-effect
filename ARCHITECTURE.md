# butterfly-effect — Architecture Reference

## What It Does

You type any real-world event in plain English. The system traces every consequence
that follows — 3, 4, even 5 steps deep — across multiple domains, with timing and
confidence at each step. The output is a causal chain visualization showing which
effects are most strongly caused (not just correlated), ranked by a mathematical
influence score.

---

## Request Flow (one query, start to finish)

```
User types: "Fed raises rates 100bps"
        ↓
[1] LLM Parsing        — Gemini/Mistral parses into structured UniversalEvent
        ↓
[2] Evidence Fetch     — DDG + Wikipedia + RSS + FRED + GDELT (concurrent, 6s timeout)
        ↓
[3] Graph Build        — LLM seeds → nodes/edges with hop depth + confidence
        ↓
[4] C-Path Algorithm   — Cumulative Causal Influence score for every node
        ↓
[5] Hybrid Simulation  — Mathematical baseline (168 steps) + Swarm corrections (12 steps)
        ↓
[6] SNN Gate           — Verifies LLM insights against graph evidence
        ↓
[7] SSE Stream         — Streams all stages to frontend in real-time
        ↓
[8] React Flow Graph   — Interactive causal chain visualization
```

---

## Backend Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Web framework | FastAPI (Python 3.10) | Async API, SSE streaming |
| LLM primary | Google Gemini 2.5-flash | Event parsing + insights |
| LLM fallback | Mistral small-latest | When Gemini rate-limited |
| LLM fallback 2 | Anthropic Claude | Tertiary fallback |
| Graph DB | Neo4j 5 (optional) | Persistent knowledge graph |
| Graph fallback | NetworkX in-memory | When Neo4j not running |
| Relational DB | PostgreSQL 15 (optional) | Event storage |
| DB fallback | SQLite (aiosqlite) | When Postgres not running |
| Cache | Redis 7 (optional) | Result caching, Celery broker |
| Cache fallback | fakeredis in-memory | When Redis not running |
| Task queue | Celery + beat | Background ingestion (FRED/GDELT every 15min) |
| NLP | spaCy (en_core_web_sm) | Entity extraction from evidence |
| HTTP client | httpx (async) | All external API calls |
| Validation | Pydantic v2 | All data models |
| Logging | loguru | Structured logging |

## Frontend Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | Next.js 14 (App Router) | React SSR |
| Language | TypeScript strict | Type safety |
| Styling | Tailwind CSS | Dark theme (#0a0e1a) |
| Graph | ReactFlow + Dagre | Interactive causal graph |
| Animation | Framer Motion | Stage transitions |
| State | Zustand | Global UI state |
| Icons | Lucide React | UI icons |

---

## Data Sources (Evidence Gathering)

All sources run concurrently with a 6-second hard timeout.

### Free, No Key Required
| Source | What It Provides | Timeout |
|--------|-----------------|---------|
| DuckDuckGo (ddgs) | Live web search, 5 results per query | 4s |
| Wikipedia REST API | Article summaries for key entities | 4s |
| BBC RSS feeds | World/business/health/tech news | 3s per feed |
| TechCrunch RSS | Technology news | 3s |
| ReliefWeb API | Humanitarian situation reports | 4s |
| GDELT Project API | 250M+ global news events, geopolitics | 3s |

### Requires API Key (in backend/.env)
| Source | Key Variable | What It Provides |
|--------|-------------|-----------------|
| FRED (St. Louis Fed) | FRED_API_KEY | Real economic time-series: FEDFUNDS, MORTGAGE30US, HOUST, UNRATE, T10Y2Y |
| ACLED | ACLED_API_KEY + ACLED_EMAIL | Armed conflict event data with fatality counts |
| NewsAPI | NEWS_API_KEY | Global news aggregation |

### LLM Keys (at least one required)
| Provider | Key Variable | Free Tier |
|----------|-------------|-----------|
| Google Gemini | GEMINI_API_KEY | 15 req/min, 1M tokens/day |
| Mistral | MISTRAL_API_KEY | Free on La Plateforme |
| Anthropic | ANTHROPIC_API_KEY | Paid only |

---

## Algorithms

### 1. C-Path — Cumulative Causal Influence
**File:** `backend/butterfly/causal/cpath.py`
**Based on:** Liu & Li (2012) cascade influence methodology

Calculates how much causal influence flows from the root event to every reachable
node in the DAG. Unlike simple hop-counting, C-Path accounts for edge confidence
at every step.

```
CCI(node) = sum over predecessors: CCI(pred) × edge_weight × alpha^distance
alpha = 0.85 (decay factor, same convention as PageRank)
```

A node 4 hops away with high-confidence edges can score higher than a 2-hop node
with weak edges. This is what makes the "butterfly effects" mathematically traceable.

Output: CCI score 0–1 for every node. Root = 1.0.

### 2. ESAA — Event Sourcing for Autonomous Agents
**File:** `backend/butterfly/simulation/esaa.py`

Agents never mutate simulation state directly. They emit structured `AgentIntention`
objects which are validated by the `ESAAOrchestrator` before being applied.

Rules enforced per intention:
- Variable must exist in environment
- Delta bounded to ±1.0
- Direction must match delta sign
- Reason string required (min 5 chars)

Every decision (accepted or rejected) is appended to `data/activity_{run_id}.jsonl`.
The log is sealed with an RFC 8785 canonical JSON + SHA-256 hash for tamper detection.
`verify_run(run_id)` replays the log and checks the hash.

### 3. Hybrid Simulation
**File:** `backend/butterfly/simulation/universal_runner.py`

Two-layer simulation:
1. **Mathematical baseline** (168 steps = 1 week): exponential decay per hop with
   Gaussian noise (2% std dev, grows with hop depth) and confidence decay over time.
   Formula: `effect = severity × 0.7^hop × e^(-0.015 × (step - peak)) + noise`
2. **Agent swarm corrections** (12 steps): specialist agents (Market, Policy,
   SupplyChain, Energy, Human) in bullish/bearish pairs apply delta corrections
   to the math baseline. Weight = 0.3 (swarm modifies, doesn't override).

Final: `timeline_a = math_baseline + swarm_corrections`, `timeline_b = math_baseline`
Diff = true causal effect including agent dynamics.

### 4. Agent Swarm with Memory Depth Reduction
**File:** `backend/butterfly/simulation/agent_swarm.py`

Each agent sees only the last k=3 arguments from the shared `DebateTranscript`
before generating its response. This prevents chaotic divergence in long debates.

Opposing pressure detection: if 2+ of last 3 window entries oppose the current
direction, the agent's magnitude is multiplied by 0.6 (dampened).

Delta is always computed from CCI scores — never from LLM output. The LLM only
generates the `reason` text field.

### 5. SNN Verification Gate
**File:** `backend/butterfly/causal/snn_gate.py`

Before any LLM insight is accepted:
1. Extract key terms from insight text
2. Find matching nodes in the DAG
3. Check their CCI scores

Rules:
- No matching nodes → confidence forced to 0.0 (hallucination blocked)
- CCI < 0.3 → confidence capped at 0.3 (weak evidence)
- CCI ≥ 0.3 → confidence passes through unchanged

### 6. Dagre Hierarchical Layout
**File:** `frontend/components/graph/utils/graphTransforms.ts`

Uses `@dagrejs/dagre` (Sugiyama-style algorithm) for top-to-bottom DAG layout.
Node spacing: 80px horizontal, 120px vertical. Ensures causal depth is visually
clear — root at top, 4th-order effects at bottom.

### 7. Predictability Horizon
**File:** `backend/butterfly/simulation/universal_runner.py`

Each hop roughly doubles uncertainty. Horizon = `min(168, 24 × 2^(4 - max_hop))`.
- 1-hop chain: 96h horizon (high confidence)
- 2-hop chain: 48h horizon (medium)
- 3+ hop chain: 24h horizon (low — treat as directional signal)

Shown as a shaded zone on the temporal replay scrubber.

---

## Key Data Models

### UniversalEvent (LLM output)
```python
title: str
domain: list[str]          # geopolitics, economics, health, technology, etc.
primary_actors: list[str]  # China, Federal Reserve, WHO
affected_systems: list[str]
geographic_scope: list[str]
time_horizon: str          # hours | days | weeks | months | years
severity: str              # minor | moderate | major | catastrophic
causal_seeds: list[str]    # 3-5 non-obvious first dominoes
data_fetch_queries: list[str]
confidence: float          # 0-1
```

### Graph Node (sent to frontend)
```python
id: str
type: str          # Event | Metric | Entity | Policy
label: str
hop: int           # 0=root, 1=1st order, 2=2nd order, 3=3rd order
confidence: float  # causal confidence
strength: float    # edge strength from parent
severity: str      # on root node only
value: float       # real FRED value if available
delta: float       # change from previous period
fred_series: str   # e.g. "FEDFUNDS" if FRED data
```

### Graph Edge (sent to frontend)
```python
id: str
source: str
target: str
strength: float
latency_hours: int
confidence: [float, float]  # [lower, upper] CI
relationship_type: str      # TRIGGERS | CAUSES | INFLUENCES | CORRELATES_WITH | DISRUPTS | DEPENDS_ON | ...
domain_crossing: bool       # True when source.domain != target.domain — these are butterfly effects
```

---

## Infrastructure (with Docker)

```yaml
# docker-compose.yml
postgres:  port 5432  — event storage
redis:     port 6379  — caching + Celery broker
neo4j:     port 7474 (browser), 7687 (bolt) — knowledge graph
```

## Infrastructure (without Docker — current default)

| Service | Replacement | Notes |
|---------|-------------|-------|
| PostgreSQL | SQLite at data/butterfly.db | Full read/write |
| Redis | fakeredis in-memory | Caching works, lost on restart |
| Neo4j | NetworkX in-memory | Graph not persisted |

---

## File Structure

```
butterfly-effect/
├── backend/butterfly/
│   ├── api/
│   │   ├── analyze.py          ← Main SSE endpoint + all pipeline stages
│   │   └── events.py           ← Event CRUD
│   ├── causal/
│   │   ├── cpath.py            ← C-Path CCI algorithm
│   │   ├── dag.py              ← NetworkX DAG builder
│   │   ├── log_extractor.py    ← Simulation → CausalChain
│   │   └── snn_gate.py         ← Anti-hallucination verification
│   ├── db/
│   │   ├── postgres.py         ← SQLAlchemy async + SQLite fallback
│   │   ├── redis.py            ← Redis async + fakeredis fallback
│   │   └── neo4j.py            ← Neo4j driver + NetworkX fallback
│   ├── extraction/
│   │   ├── ner.py              ← spaCy NER
│   │   ├── normalizer.py       ← Entity name normalization
│   │   └── relations.py        ← Causal relation extraction (14 types)
│   ├── ingestion/
│   │   ├── universal_fetcher.py ← DDG + Wikipedia + RSS + ReliefWeb
│   │   ├── fred.py             ← FRED economic data
│   │   ├── gdelt.py            ← GDELT news events
│   │   └── scheduler.py        ← Celery beat tasks
│   ├── llm/
│   │   ├── providers.py        ← Gemini → Mistral → Anthropic router
│   │   ├── event_parser.py     ← Plain text → UniversalEvent
│   │   └── insight_generator.py ← CausalChain → 3 LLM insights
│   ├── simulation/
│   │   ├── esaa.py             ← ESAA orchestrator + crypto verification
│   │   ├── universal_runner.py ← Hybrid simulation (math + swarm)
│   │   └── agent_swarm.py      ← Mesa agents with k=3 memory window
│   └── main.py                 ← FastAPI app factory
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx            ← Main app (idle → streaming → done)
│   │   ├── demo/page.tsx       ← Pre-loaded demo (no backend)
│   │   └── analyze/page.tsx    ← Redirects to /?q=...
│   └── components/
│       ├── graph/
│       │   ├── CausalGraphCanvas.tsx  ← ReactFlow wrapper + legend
│       │   ├── nodes/                 ← EventNode, MetricNode, EntityNode, PolicyNode
│       │   ├── edges/                 ← CausalEdge (animated dot), InfluenceEdge
│       │   ├── controls/              ← GraphToolbar (zoom + layout)
│       │   └── utils/graphTransforms.ts ← Dagre layout
│       ├── AnalysisStream.tsx  ← Stage progress indicators
│       ├── InsightCard.tsx     ← 2nd/3rd/4th order insight cards
│       ├── TemporalReplay.tsx  ← Timeline scrubber + predictability horizon
│       └── EvidencePanelNew.tsx ← Node evidence panel
│
└── data/
    ├── butterfly.db            ← SQLite (auto-created)
    ├── activity_{run_id}.jsonl ← ESAA immutable log per run
    └── swarm_{run_id}.jsonl    ← Swarm agent log per run
```

---

## Environment Variables (backend/.env)

```bash
# LLM (at least one required)
GEMINI_API_KEY=...      # Free: aistudio.google.com/app/apikey
MISTRAL_API_KEY=...     # Free: console.mistral.ai
ANTHROPIC_API_KEY=...   # Paid

# Data sources (optional — system works without them)
FRED_API_KEY=...        # Free: fred.stlouisfed.org/docs/api/api_key.html
ACLED_API_KEY=...       # Free: acleddata.com
ACLED_EMAIL=...
NEWS_API_KEY=...        # Free tier: newsapi.org

# Databases (optional — SQLite/fakeredis/NetworkX used as fallbacks)
POSTGRES_URL=postgresql+asyncpg://butterfly:butterfly@localhost:5432/butterfly
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=butterfly_dev

# App
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

---

## How to Run

```bash
# Backend (Terminal 1)
cd backend
./venv/Scripts/python.exe -m uvicorn butterfly.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (Terminal 2)
cd frontend
npm run dev

# Open: http://localhost:3000
# Demo (no backend): http://localhost:3000/demo
```

---

## What's Not Yet Complete

| Feature | Status | Notes |
|---------|--------|-------|
| Neo4j persistence | Needs Docker | Graph resets on restart |
| FRED in live queries | Working | Requires FRED_API_KEY |
| Celery background ingestion | Needs Redis | Workers dormant without broker |
| Evidence panel (live data) | Working | Shows fetched evidence per node |
| Shareable URLs | Working | GET /api/v1/analyze/{run_id} |
| Crypto verification | Working | GET /api/v1/analyze/{run_id}/verify |

## Evidence → Graph Flow (current)

```
Evidence (DDG + Wikipedia + RSS + arXiv + OpenAlex + NOAA + World Bank)
    ↓ spaCy NER (loaded at startup, zero per-request cost)
    ↓ RelationExtractor (14 relation types — CAUSES, TRIGGERS, DISRUPTS, etc.)
    → Evidence nodes + typed edges (primary source)

LLM Pass 1 (causal_seeds)
    → Fill gaps where evidence is sparse (secondary source)

LLM Pass 2 (parse_deep) — runs concurrently with evidence fetch
    → deep_causal_seeds → hop-3/4 nodes
    → cross_domain_links → typed edges between domains
    → non_obvious_actors → hop-4 nodes

domain_crossing: bool on every edge
    → True when source.domain != target.domain
    → These are the butterfly effects worth highlighting
```

## SNN Verification (current)

Checks insight key terms against FETCHED EVIDENCE TEXT (not the LLM graph).
- ≥40% term match in evidence → confidence passes through
- Partial match → confidence scaled by match ratio
- No match → confidence capped at 0.3
- No evidence fetched → confidence capped at 0.4

## Pipeline Stages (extracted modules)

```
pipeline/
  stage_parse.py     ← LLM parse + deep parse task (concurrent)
  stage_fetch.py     ← All evidence sources (7s timeout)
  stage_graph.py     ← NER + LLM seeds + deep seeds + FRED
  stage_simulate.py  ← C-Path + hybrid simulation
  stage_insights.py  ← LLM insights + SNN verification
```

Each stage has independent error handling — one stage failing doesn't kill the stream.

## LLM Adapter Interface

```python
# butterfly/llm/adapter.py
class LLMAdapter(Protocol):
    async def complete(self, system: str, user: str, max_tokens: int) -> str: ...
    @property
    def name(self) -> str: ...

# Implementations: GeminiAdapter, MistralAdapter, AnthropicAdapter
# Usage: complete_with_fallback(system, user) — tries all in order
```

If any provider changes their API, only one adapter class breaks.

## API Endpoints

```
POST /api/v1/analyze              ← Main SSE stream
GET  /api/v1/analyze/{run_id}     ← Cached result
GET  /api/v1/analyze/{run_id}/verify    ← Cryptographic verification
POST /api/v1/analyze/{run_id}/validate  ← Submit ground-truth validation
GET  /api/v1/admin/esaa-report    ← Aggregate swarm bias analysis
```

## Validation & Learning Loop

```
POST /api/v1/analyze/{run_id}/validate
Body: {"node_id": "housing_starts", "actual_direction": "down", "actual_magnitude": 0.18}

Stored in SQLite validations table.
After 100 validations → confidence weights can be retrained.
```

## ESAA Log Analyzer

```bash
python -m butterfly.simulation.esaa_analyzer data/
```

Reads all `activity_*.jsonl` files and reports:
- Variables with high rejection rates (systematic bias)
- Variables with low consensus (chaotic swarm)
- Agents with high rejection rates (miscalibrated)

## Performance Profile

| Stage | Current | Target | Fix |
|-------|---------|--------|-----|
| LLM parse | 2-4s | 0.8s | gemini-2.0-flash; deep parse runs concurrently |
| Evidence fetch | 6s | 3s | Domain-adaptive sources; 3s timeout |
| Graph build | 0.1s | 0.1s | ✓ |
| C-Path | 0.05s | 0.05s | ✓ |
| Math simulation | 0.2s | 0.2s | ✓ |
| Swarm (12 steps) | 0.3s | 0.3s | ✓ |
| Insight gen | 2-3s | 1s | Runs during simulation (overlap) |
| **Total** | **~11-14s** | **~6-8s** | |

## What's Not Yet Complete

| Feature | Status | Notes |
|---------|--------|-------|
| Neo4j persistence | Needs Docker | Graph resets on restart |
| FRED in live queries | Working | Requires FRED_API_KEY |
| Celery background ingestion | Needs Redis | Workers dormant without broker |
| Evidence panel (live data) | Working | Shows fetched evidence per node |
| Shareable URLs | Working | GET /api/v1/analyze/{run_id} |
| Crypto verification | Working | GET /api/v1/analyze/{run_id}/verify |
| Ground-truth validation | Working | POST /api/v1/analyze/{run_id}/validate |
| ESAA log analysis | Working | GET /api/v1/admin/esaa-report |
| Confidence retraining | Not built | Needs 100+ validations first |
| 5-hop chains | Working | Two-pass LLM parsing adds hop-3/4 nodes |
