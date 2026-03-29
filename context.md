# CONTEXT.md — butterfly-effect AI IDE Context File

> **Instructions for AI IDE (Cursor / Windsurf / Copilot / Claude Code):**
> Read this entire file before writing any code. This is the single source of truth
> for architecture decisions, naming conventions, data models, and build priorities.
> When in doubt, refer back here. Do NOT deviate from these decisions without
> flagging the conflict explicitly.

---

## 1. PROJECT IDENTITY

**Name:** butterfly-effect
**Tagline:** A causal inference engine that makes invisible cascade effects visible, traceable, and quantifiable.
**Core value prop:** Run an event. Run the counterfactual (no event). Subtract. Show the *true causal chain* with confidence scores and evidence paths.
**GitHub:** https://github.com/Om7035/butterfly-effect
**Author:** Om Kawale (@Om7035)
**Status:** Active development — follow PHASES.md strictly

---

## 2. TECH STACK — CANONICAL (DO NOT CHANGE WITHOUT REASON)

### Backend
| Concern | Technology | Version | Notes |
|---------|-----------|---------|-------|
| Web framework | FastAPI | 0.111+ | Async everywhere. No Flask. |
| Python | CPython | 3.11+ | Use `match` statements, walrus operator |
| Task queue | Celery | 5.3+ | With Redis broker |
| Cache/broker | Redis | 7.x | Via Docker |
| Relational DB | PostgreSQL | 15+ | Via Docker |
| Graph DB | Neo4j | 5.x Community | Via Docker |
| ORM | SQLAlchemy | 2.x | Async sessions only |
| Neo4j driver | neo4j (official) | 5.x | |
| Validation | Pydantic | 2.x | All models use `BaseModel` |
| NLP | spaCy | 3.7+ | Model: en_core_web_trf |
| Causal inference | DoWhy | 0.11+ | Core identification engine |
| Bayesian networks | pgmpy | 0.1.25+ | DAG modeling |
| Causal ML | causalml | 0.15+ | Heterogeneous effects |
| Time-series | statsmodels | 0.14+ | Granger, VAR |
| Agent simulation | Mesa | 2.x | ABM framework |
| HTTP client | httpx | 0.27+ | Async, for API polling |
| Testing | pytest + pytest-asyncio | latest | 90%+ coverage target |
| Linting | ruff | latest | `ruff check .` must pass |
| Type checking | mypy | latest | Strict mode |

### Frontend
| Concern | Technology | Version | Notes |
|---------|-----------|---------|-------|
| Framework | Next.js | 14+ (App Router) | No Pages Router |
| Language | TypeScript | 5.x | Strict mode |
| Styling | Tailwind CSS | 3.x | No custom CSS unless necessary |
| Components | shadcn/ui | latest | Use existing components first |
| Graph vis | Sigma.js | 3.x | Main ripple map |
| Causal map | Cytoscape.js | 3.x | Detailed causal graph view |
| Charts/scrubber | D3.js | 7.x | Temporal scrubber only |
| API client | TanStack Query | 5.x | All data fetching |
| State | Zustand | 4.x | Global UI state only |
| Forms | React Hook Form + Zod | latest | |
| Icons | Lucide React | latest | |
| Testing | Vitest + Testing Library | latest | |

### Infrastructure
| Concern | Technology | Notes |
|---------|-----------|-------|
| Containers | Docker + Docker Compose | All services containerized |
| CI | GitHub Actions | Runs on every PR |
| Secrets | .env files (never committed) | .env.example always up to date |

---

## 3. REPOSITORY STRUCTURE

```
butterfly-effect/
├── README.md
├── CONTRIBUTING.md
├── LICENSE
├── docker-compose.yml
├── docker-compose.test.yml        # Test-specific compose
├── .env.example                   # All env vars documented here
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Test + lint on PR
│       └── release.yml            # Tag → release
│
├── backend/
│   ├── butterfly/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app factory
│   │   ├── config.py              # Pydantic Settings
│   │   ├── db/
│   │   │   ├── neo4j.py           # Async Neo4j driver wrapper
│   │   │   ├── postgres.py        # SQLAlchemy async engine
│   │   │   ├── redis.py           # Redis connection
│   │   │   └── schema.cypher      # Neo4j constraint/index init
│   │   ├── models/
│   │   │   ├── event.py           # Event Pydantic models
│   │   │   ├── causal_edge.py     # CausalEdge model (canonical)
│   │   │   ├── agent.py           # Agent model
│   │   │   └── simulation.py      # SimulationRun model
│   │   ├── ingestion/
│   │   │   ├── base.py            # BaseIngester ABC
│   │   │   ├── fred.py            # FRED API
│   │   │   ├── edgar.py           # SEC EDGAR
│   │   │   ├── gdelt.py           # GDELT
│   │   │   ├── news.py            # NewsAPI
│   │   │   └── scheduler.py       # Celery beat schedule
│   │   ├── extraction/
│   │   │   ├── ner.py             # Named entity recognition
│   │   │   ├── relations.py       # Relation extraction
│   │   │   └── graph_builder.py   # Neo4j graph loader
│   │   ├── causal/
│   │   │   ├── dag.py             # pgmpy DAG builder
│   │   │   ├── identification.py  # DoWhy CausalModel wrapper
│   │   │   ├── estimation.py      # Effect size calculation
│   │   │   ├── refutation.py      # Automated refutation suite
│   │   │   └── counterfactual.py  # Timeline A/B diff engine
│   │   ├── simulation/
│   │   │   ├── agents.py          # Mesa Agent subclasses
│   │   │   ├── model.py           # Mesa Model
│   │   │   └── runner.py          # Parallel sim runner
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py            # FastAPI dependencies
│   │   │   ├── events.py          # /api/events routes
│   │   │   ├── causal.py          # /api/causal routes
│   │   │   ├── simulation.py      # /api/simulation routes
│   │   │   └── health.py          # /health route
│   │   └── worker.py              # Celery app
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_ingestion/
│   │   ├── test_extraction/
│   │   ├── test_causal/
│   │   ├── test_simulation/
│   │   ├── test_api/
│   │   └── fixtures/
│   │       ├── fed_2022.json      # Historical event fixture
│   │       ├── texas_storm_2021.json
│   │       └── covid_supply_chain.json
│   ├── pyproject.toml
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx               # Dashboard / home
│   │   ├── analysis/
│   │   │   └── [id]/
│   │   │       └── page.tsx       # Causal chain viewer
│   │   └── demo/
│   │       └── page.tsx           # Demo mode (no API key needed)
│   ├── components/
│   │   ├── ui/                    # shadcn components (auto-generated)
│   │   ├── CausalGraph.tsx        # Sigma.js ripple visualization
│   │   ├── TemporalScrubber.tsx   # D3 time slider
│   │   ├── EvidencePanel.tsx      # Source trail drawer
│   │   ├── CounterfactualDiff.tsx # Side-by-side A/B view
│   │   ├── ConfidenceBar.tsx      # Visual confidence indicator
│   │   ├── EventInput.tsx         # Event submission form
│   │   └── SimulationStatus.tsx   # Running/complete indicator
│   ├── lib/
│   │   ├── api.ts                 # API client (typed)
│   │   ├── graph.ts               # Sigma/Cytoscape utils
│   │   └── types.ts               # Shared TypeScript types
│   ├── store/
│   │   └── analysis.ts            # Zustand store
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
│
└── docs/
    ├── CONTEXT.md                 # This file
    ├── PHASES.md                  # Phased build plan
    ├── ARCHITECTURE.md            # Deep architecture docs
    └── VALIDATION.md              # Backtesting methodology
```

---

## 4. CANONICAL DATA MODELS

These are locked. All code must conform to these models.

### CausalEdge (core model — everything derives from this)

```python
# backend/butterfly/models/causal_edge.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class CausalEdge(BaseModel):
    edge_id: str                              # "causal_{source}_{target}_{timestamp}"
    source_node_id: str                       # Neo4j node ID
    target_node_id: str                       # Neo4j node ID
    relationship_type: str                    # "influences_price" | "triggers_sentiment" | ...
    strength_score: float = Field(ge=0, le=1) # 0.0 = no effect, 1.0 = deterministic
    time_decay_factor: float                  # How fast effect fades
    latency_hours: float                      # Expected hours until effect manifests
    counterfactual_delta: float               # A(t) - B(t) at effect peak
    confidence_interval: tuple[float, float]  # (lower, upper) — 95% CI
    evidence_path: list[str]                  # Source IDs supporting this edge
    refutation_passed: bool                   # Did automated refutation tests pass?
    created_at: datetime
    updated_at: Optional[datetime] = None
```

### Event (input model)

```python
class Event(BaseModel):
    event_id: str
    title: str
    description: str
    source: str                        # "fred" | "edgar" | "gdelt" | "news" | "manual"
    source_url: Optional[str]
    occurred_at: datetime
    entities: list[str]                # Extracted entity IDs
    raw_text: str
    processed: bool = False
```

### SimulationRun

```python
class SimulationRun(BaseModel):
    run_id: str
    event_id: str
    status: str                        # "queued" | "running" | "complete" | "failed"
    timeline_a_id: str                 # Event happens
    timeline_b_id: str                 # Counterfactual
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    causal_edges: list[CausalEdge] = []
    error: Optional[str] = None
```

### Neo4j Node Labels
- `Event` — external events (Fed decisions, news, filings)
- `Entity` — extracted entities (companies, people, sectors)
- `Metric` — quantitative measures (mortgage rate, employment, etc.)
- `Policy` — policy instruments
- `Agent` — simulation agents

### Neo4j Relationship Types
- `INFLUENCES` — general causal influence
- `TRIGGERS` — event triggers another event
- `CORRELATES_WITH` — statistical correlation (not causal)
- `CAUSED_BY` — validated causal link (post-DoWhy)
- `SIMULATED_REACTION` — agent simulation output

---

## 5. API CONTRACT

### Base URL: `/api/v1`

#### Events
```
POST   /api/v1/events              # Submit new event for analysis
GET    /api/v1/events              # List events (paginated)
GET    /api/v1/events/{event_id}   # Get single event + status
```

#### Causal Analysis
```
POST   /api/v1/causal/analyze      # Start causal analysis on event
GET    /api/v1/causal/{event_id}   # Get causal chain for event
GET    /api/v1/causal/{event_id}/edges     # Get all causal edges
GET    /api/v1/causal/{event_id}/evidence  # Get evidence paths
```

#### Simulation
```
POST   /api/v1/simulation/run      # Start simulation (queues Celery job)
GET    /api/v1/simulation/{run_id} # Get simulation status + results
GET    /api/v1/simulation/{run_id}/diff    # Get counterfactual diff
```

#### Health
```
GET    /health                     # { status: "ok", neo4j: bool, redis: bool }
```

---

## 6. ENVIRONMENT VARIABLES

```bash
# backend/.env (never commit this — use .env.example)

# Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=butterfly_dev
POSTGRES_URL=postgresql+asyncpg://butterfly:butterfly@localhost:5432/butterfly
REDIS_URL=redis://localhost:6379/0

# Data APIs (all free tier unless noted)
FRED_API_KEY=          # https://fred.stlouisfed.org/docs/api/api_key.html
NEWS_API_KEY=          # https://newsapi.org — $50/mo for production
# GDELT and SEC EDGAR require no key

# App
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
SECRET_KEY=dev-secret-key-change-in-prod

# Simulation
MAX_AGENTS=500
SIMULATION_TIMEOUT_SECONDS=300
MAX_PARALLEL_SIMULATIONS=3
```

---

## 7. CODING CONVENTIONS

### Python
- All async where possible (`async def` everywhere in API layer)
- Type hints on all function signatures — no exceptions
- Docstrings on all public functions (Google style)
- Use `loguru` for logging, not `print`
- Raise custom exceptions from `butterfly/exceptions.py`, not generic ones
- Never use `except Exception` without re-raising or logging
- All database calls wrapped in try/except with specific error types
- Use `@lru_cache` for expensive, static computations (DAG builds)

### TypeScript
- Strict mode always
- No `any` types — use `unknown` and narrow
- All API responses typed with generated types (from OpenAPI schema)
- Components: function declarations, not arrow functions at top level
- Props interfaces named `{ComponentName}Props`
- All async operations wrapped in try/catch

### Git
- Branch naming: `feat/`, `fix/`, `chore/`, `docs/`
- Commit messages: Conventional Commits format
- No direct commits to `main` — all PRs
- Each PR must pass: `ruff check`, `mypy`, `pytest`, `npm run type-check`

---

## 8. TESTING STRATEGY

### Unit Tests (target: 80% coverage)
- Test every function in `causal/` with synthetic data
- Test ingestion parsers against fixture JSON files
- Test NER pipeline on known text samples
- Mock external API calls (httpx mock)

### Integration Tests
- Test full pipeline: ingest → extract → graph → causal → API response
- Use `docker-compose.test.yml` for isolated test environment
- Test Neo4j queries against a test database with seed data

### Validation Tests (critical — these prove the product works)
- `tests/validation/test_fed_2022.py` — backtest 2022 Fed rate cycle
- `tests/validation/test_texas_storm.py` — backtest 2021 ERCOT failure
- Each validation test asserts:
  - Causal chain has ≥3 hops
  - Counterfactual delta is non-zero for affected metrics
  - Effect direction matches historical consensus
  - Refutation tests pass for at least 80% of edges

---

## 9. IMPORTANT ARCHITECTURAL DECISIONS (DO NOT REVERSE)

### Decision 1: Empirically constrained agents
Mesa agents do NOT use free-form LLM generation for reaction functions.
Each agent type has a reaction function grounded in historical data.
Reason: LLMs hallucinate plausible-sounding but statistically invalid reactions.
LLMs may only be used to *interpret* pre-defined behavioral outputs for the UI.

### Decision 2: DoWhy is the source of truth for causality
Correlation ≠ causation. Every causal edge MUST pass DoWhy identification
before being stored as a `CAUSED_BY` relationship in Neo4j.
Granger causality is used for hypothesis generation only.
Reason: Without formal identification, the product is just a correlation mapper.

### Decision 3: Evidence paths are non-optional
Every causal edge must have at least one entry in `evidence_path`.
No edge may be stored without a traceable source.
Reason: Enterprise customers cannot use conclusions they cannot explain.

### Decision 4: Counterfactual diff, not absolute prediction
We do not predict "what will happen." We answer "what would be different."
Output is always relative: A(t) - B(t).
Reason: Absolute predictions are falsifiable and will be wrong. Relative
counterfactual reasoning is more defensible and more valuable.

### Decision 5: Open source everything except the training data
All code is MIT licensed. Any proprietary causal graph data built from
customer usage stays private per customer.
Reason: Open source builds trust with the exact customers who are skeptical
of black-box systems. Community validation strengthens credibility.

---

## 10. PHASE REFERENCE (see PHASES.md for full detail)

| Phase | Name | Duration | Goal |
|-------|------|----------|------|
| 1 | Foundation | 7 days | Working data pipeline + knowledge graph |
| 2 | Causal Core | 7 days | DoWhy counterfactual on 1 real event |
| 3 | Simulation | 7 days | Mesa agent simulation + diff engine |
| 4 | API Layer | 5 days | Full REST API + async job processing |
| 5 | Frontend | 7 days | Dashboard + causal graph visualization |
| 6 | Validation | 5 days | Backtest 3 historical events |
| 7 | Polish + Launch | 5 days | GitHub launch, demo mode, documentation |

---

## 11. KNOWN HARD PROBLEMS (READ BEFORE BUILDING)

### Problem 1: Causal identification from observational data
You cannot run RCTs on macro events. You must use observational causal inference.
DoWhy's `backdoor` identification requires you to know and measure confounders.
If a confounder is unobserved, your estimate is biased.
Mitigation: Be transparent about assumed DAG structure. Use sensitivity analysis.

### Problem 2: LLM-backed agents drift toward herd behavior
If you use LLMs for agents, they cluster toward consensus too fast.
This is a known failure mode in MiroFish-style systems.
Mitigation: Use empirical reaction functions. Add noise injection to agents.

### Problem 3: Neo4j performance at scale
Graph traversals degrade on very large graphs (>1M nodes).
Mitigation: Index on node labels and edge types. Use parameterized Cypher.
Profile queries with `EXPLAIN` before deploying any complex traversal.

### Problem 4: Validation is philosophically hard
The fundamental problem of causal inference: you can never observe the
counterfactual. You can only approximate it.
Mitigation: 4-layer validation stack (see VALIDATION.md). Be honest in UI
about confidence intervals. Never claim certainty.

---

## 12. DEMO DATA

For demo mode and initial testing, use these pre-built scenarios:

### Scenario 1: 2022 Fed Rate Hike Cycle
- Event: FOMC statement June 2022, 75bps hike
- Expected chain: Fed → Treasury → Mortgage → Housing → Construction → Labor
- Data sources: FRED (all public), news archives
- Ground truth: CBO and Fed published post-hoc estimates exist for comparison

### Scenario 2: 2021 Texas Winter Storm (ERCOT failure)
- Event: Grid failure February 2021
- Expected chain: ERCOT → Energy prices → Supply chain → Manufacturing → Employment
- Data sources: GDELT, SEC filings, BLS data
- Ground truth: Texas Legislature post-mortem reports

### Scenario 3: COVID Supply Chain Shock (2021-2022)
- Event: Semiconductor shortage declaration
- Expected chain: Shortage → Auto production → Dealer inventory → Used car prices → CPI
- Data sources: SEC filings, FRED, news
- Ground truth: Well-documented with multiple academic papers

---

*Last updated: 2026-03-29*
*Maintained by: Om Kawale (@Om7035)*
*This file is the AI IDE's primary reference — keep it up to date as decisions change.*