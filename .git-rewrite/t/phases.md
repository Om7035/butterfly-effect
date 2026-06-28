# PHASES.md — butterfly-effect Build Plan

> **Experimental Builder Framework**
> 1. Start before ready → 2. Build small → 3. Test quickly
> 4. Capture feedback → 5. Improve fast → 6. Repeat aggressively

**Philosophy:** Every phase produces something *runnable and testable*. No phase ends
without a green test and a visible output you can show someone. We ship ugly and fix it.

---

## Overview

| Phase | Name | Days | Deliverable | Test Goal |
|-------|------|------|-------------|-----------|
| 0 | Scaffolding | 2 | Repo + Docker up | `GET /health` returns 200 |
| 1 | Data Pipeline | 5 | Live data flowing into Postgres | 50+ events ingested |
| 2 | Knowledge Graph | 5 | Entities in Neo4j with relationships | 3-hop query works |
| 3 | Causal Core | 7 | Counterfactual diff on 1 real event | Delta matches consensus ±20% |
| 4 | Simulation | 7 | Mesa agents react to an event | Diff engine runs in <5 min |
| 5 | API Layer | 5 | Full REST API + async jobs | Postman collection green |
| 6 | Frontend | 7 | Dashboard + causal graph renders | Demo loads without errors |
| 7 | Validation | 5 | 3 historical backtests pass | 2/3 within ±20% of consensus |
| 8 | Launch | 3 | GitHub public, demo live | 100 GitHub stars target |

**Total: ~46 days from zero to launched open-source product**

---

## PHASE 0 — Scaffolding

**Duration:** 2 days
**Goal:** Empty repo that runs. All dependencies installed. Docker up.
**Success metric:** `curl http://localhost:8000/health` returns `{"status": "ok"}`

---

### Prompt 0.1 — Initialize repo structure

```
You are building butterfly-effect, a causal inference engine.

Task: Create the complete repository scaffold.

Create this exact directory structure:
butterfly-effect/
├── README.md (placeholder — 3 lines)
├── docker-compose.yml
├── .env.example
├── .gitignore
├── backend/
│   ├── butterfly/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── config.py
│   ├── tests/
│   │   └── conftest.py
│   ├── pyproject.toml
│   └── requirements.txt
└── frontend/
    ├── package.json
    ├── tailwind.config.ts
    └── tsconfig.json

Rules:
- main.py: FastAPI app with only GET /health endpoint
- config.py: Pydantic Settings reading from .env
- docker-compose.yml: services for neo4j, postgres, redis only
- .env.example: document every env variable with a comment explaining it
- pyproject.toml: configure ruff + mypy in strict mode
- requirements.txt: include fastapi, uvicorn, pydantic, python-dotenv, neo4j, 
  sqlalchemy[asyncio], asyncpg, celery, redis, httpx, loguru, pytest, pytest-asyncio

Do not add anything else. Just the scaffold.
```

---

### Prompt 0.2 — Docker Compose setup

```
You are setting up docker-compose.yml for butterfly-effect.

Create a docker-compose.yml with these exact services:

1. neo4j:
   - Image: neo4j:5-community
   - Ports: 7474 (browser), 7687 (bolt)
   - Volumes: neo4j_data
   - Env: NEO4J_AUTH=neo4j/butterfly_dev
   - Health check: wget on port 7474

2. postgres:
   - Image: postgres:15-alpine
   - Ports: 5432
   - Volumes: postgres_data
   - Env: POSTGRES_DB=butterfly, POSTGRES_USER=butterfly, POSTGRES_PASSWORD=butterfly
   - Health check: pg_isready

3. redis:
   - Image: redis:7-alpine
   - Ports: 6379
   - Health check: redis-cli ping

All services on a shared network "butterfly-net".
Named volumes at the bottom.
No app services yet — those come later.
```

---

### Test 0 ✅

```bash
# Run this — all three must pass before moving to Phase 1
docker compose up -d
docker compose ps          # All 3 services: "healthy"
curl http://localhost:7474  # Neo4j browser responds
curl http://localhost:8000/health  # {"status":"ok","neo4j":false,"redis":false}
# neo4j/redis show false because backend isn't connected yet — that's fine
```

---

## PHASE 1 — Data Pipeline

**Duration:** 5 days
**Goal:** Real-world data automatically flowing into the system
**Success metric:** 50+ real events in PostgreSQL within 30 minutes of startup

---

### Prompt 1.1 — Event schema + database init

```
You are building the data layer for butterfly-effect.

Context: Read CONTEXT.md sections 4 (Data Models) and 6 (Environment Variables).

Task: Create the following files:

1. backend/butterfly/models/event.py
   - Pydantic v2 Event model (exact schema from CONTEXT.md section 4)
   - SQLAlchemy async ORM model for PostgreSQL storage
   - Both models in the same file, clearly separated

2. backend/butterfly/db/postgres.py
   - AsyncEngine using asyncpg
   - AsyncSession factory
   - create_all_tables() async function
   - get_db() dependency for FastAPI

3. backend/butterfly/db/schema.cypher
   - Neo4j constraints: unique on Event.event_id, Entity.entity_id
   - Indexes: on Event.occurred_at, Entity.name, CausalEdge.strength_score
   - Write as pure Cypher, one statement per line with comments

Rules:
- Use SQLAlchemy 2.x async syntax throughout
- All models must have __repr__ methods
- Include full type hints
- Add a brief docstring to every class
```

---

### Prompt 1.2 — FRED API ingester

```
You are building the FRED API ingester for butterfly-effect.

Context: 
- FRED API docs: https://fred.stlouisfed.org/docs/api/fred/
- Base URL: https://api.stlouisfed.org/fred
- Our Event model is in backend/butterfly/models/event.py
- Config (including FRED_API_KEY) is in backend/butterfly/config.py

Task: Create backend/butterfly/ingestion/fred.py

This module must:

1. Define a FREDIngester class that extends BaseIngester (create the ABC too)
2. Poll these specific series on each run:
   - FEDFUNDS (Fed funds rate)
   - MORTGAGE30US (30-year mortgage rate)
   - HOUST (Housing starts)
   - UNRATE (Unemployment rate)
   - T10Y2Y (Yield curve spread)
3. For each new data point, create an Event object with:
   - source = "fred"
   - title = f"FRED: {series_id} = {value}"
   - description = full context including previous value and % change
   - occurred_at = the observation date
4. Store events in PostgreSQL using async session
5. Track last-polled timestamp to avoid duplicates (store in Redis)

Error handling:
- If FRED API is down: log warning, return empty list, do NOT raise
- If rate limited: back off exponentially, retry 3 times
- If parsing fails: log the raw response and skip that series

Use httpx.AsyncClient with a timeout of 30 seconds.
Include unit tests in tests/test_ingestion/test_fred.py using httpx mock.
```

---

### Prompt 1.3 — GDELT ingester

```
You are building the GDELT ingester for butterfly-effect.

Context:
- GDELT requires no API key
- GDELT 2.0 Events API: http://api.gdeltproject.org/api/v2/doc/doc
- Query format: ?query=...&mode=artlist&format=json&maxrecords=250
- Our Event model: backend/butterfly/models/event.py

Task: Create backend/butterfly/ingestion/gdelt.py

This module must:

1. Define GDELTIngester class extending BaseIngester
2. Poll GDELT every 15 minutes for events matching these themes:
   - "ECON_TRADE" (trade events)
   - "ECON_INTEREST" (interest rate events)
   - "SUPPLY_CHAIN" (supply chain events)
   - "GEOPOLITICS" (geopolitical events)
3. For each article returned:
   - Extract: title, URL, date, tone score, goldstein scale score
   - Create Event with source="gdelt"
   - Store goldstein_scale in a metadata JSON field
4. Deduplicate by URL (check Redis cache before inserting)
5. Return count of new events ingested

Important: GDELT can return 250+ articles per query. 
Process them in batches of 50. 
Add a 100ms delay between batches to avoid hammering their servers.

Include tests using recorded GDELT response fixtures.
```

---

### Prompt 1.4 — Celery scheduler

```
You are building the Celery task scheduler for butterfly-effect.

Context:
- We have FREDIngester and GDELTIngester already built
- Redis is our broker (REDIS_URL from config)
- We want polling every 15 minutes

Task: Create these files:

1. backend/butterfly/worker.py
   - Celery app factory
   - Beat schedule: FRED every 15 min, GDELT every 15 min, EDGAR every 30 min
   - Proper timezone handling (UTC everywhere)

2. backend/butterfly/ingestion/scheduler.py
   - @celery.task for each ingester
   - Each task: instantiate ingester, call ingest(), log result
   - Tasks must be idempotent (safe to run twice)

3. Update docker-compose.yml to add:
   - celery-worker service
   - celery-beat service
   - Both depend on redis and postgres being healthy

4. Update backend/butterfly/main.py
   - Add startup event that runs create_all_tables()
   - Add /health endpoint that checks: postgres conn, neo4j conn, redis conn
   - Return {"status":"ok","postgres":bool,"neo4j":bool,"redis":bool}

Rules:
- Use Celery 5.x signatures
- Log at INFO level when task starts and ends with event count
- Add @shared_task decorator for testability
```

---

### Test 1 ✅

```bash
# Run these checks — all must pass before Phase 2

# 1. Start everything
docker compose up -d

# 2. Wait 5 minutes for first poll cycle

# 3. Check events were ingested
docker compose exec postgres psql -U butterfly -d butterfly \
  -c "SELECT source, COUNT(*) FROM events GROUP BY source;"
# Expected: fred: 5+, gdelt: 50+

# 4. Check health endpoint
curl http://localhost:8000/health
# Expected: {"status":"ok","postgres":true,"neo4j":true,"redis":true}

# 5. Run unit tests
cd backend && pytest tests/test_ingestion/ -v
# Expected: All green

# PHASE 1 GATE: 50+ events in DB, all tests green → proceed to Phase 2
```

**Feedback to capture after Phase 1:**
- [ ] Which data source gives the most useful events?
- [ ] Are events being deduplicated correctly?
- [ ] Is the polling rate sustainable (no rate limits hit)?
- [ ] Does the Event schema need any fields added?

---

## PHASE 2 — Knowledge Graph

**Duration:** 5 days
**Goal:** Extract entities from events and build a navigable causal knowledge graph in Neo4j
**Success metric:** Run a Cypher query that finds a 3-hop causal chain starting from a Fed event

---

### Prompt 2.1 — spaCy NER pipeline

```
You are building the NLP extraction pipeline for butterfly-effect.

Context:
- We have Event objects in PostgreSQL (see models/event.py)
- We want to extract entities and relationships from event text
- Target Neo4j node labels: Event, Entity, Metric, Policy

Task: Create backend/butterfly/extraction/ner.py

Requirements:
1. Load spaCy model: en_core_web_trf (transformer-based, most accurate)
   - Add fallback to en_core_web_sm if trf not available (for CI/CD)
2. EntityExtractor class with method extract(text: str) -> list[ExtractedEntity]
3. ExtractedEntity dataclass: {text, label, start, end, confidence}
4. Map spaCy labels to our node labels:
   - ORG → Entity (company/institution)
   - GPE → Entity (country/region)  
   - MONEY, PERCENT → Metric
   - LAW → Policy
   - EVENT → Event (reference to another event)
   - PERSON → Entity (individual)
5. Post-processing: normalize entity names
   - "Federal Reserve" = "Fed" = "FOMC" → normalize to "Federal Reserve"
   - "United States" = "US" = "U.S." → "United States"
   - Keep a normalization dict in extraction/normalizer.py
6. Return confidence score per entity (spaCy's scorer output)

Include tests with 5 sample texts covering finance, policy, supply chain.
Test that Fed/FOMC normalization works.
```

---

### Prompt 2.2 — Relationship extraction

```
You are building the relationship extraction module for butterfly-effect.

Context:
- We have EntityExtractor from ner.py
- We need to find causal relationships between entities in text
- These become edges in our Neo4j graph

Task: Create backend/butterfly/extraction/relations.py

Requirements:
1. RelationExtractor class
2. extract_relations(text: str, entities: list[ExtractedEntity]) -> list[ExtractedRelation]
3. ExtractedRelation: {source_entity, target_entity, relation_type, confidence, evidence_text}
4. Implement two extraction strategies:
   
   Strategy A — Pattern matching (fast, high precision):
   - Detect causal language patterns using regex + spaCy dependency parsing:
     "X caused Y", "X led to Y", "X resulted in Y", "X triggered Y",
     "due to X, Y", "following X, Y", "X drove Y higher/lower"
   - Map patterns to relationship types: CAUSES, TRIGGERS, INFLUENCES
   
   Strategy B — Co-occurrence + proximity (broad, lower precision):
   - If two named entities appear within 50 tokens AND a directional verb is present
   - Tag these as CORRELATES_WITH (not causal — flagged for DoWhy validation later)

5. Output: list of ExtractedRelation objects, sorted by confidence DESC
6. Minimum confidence threshold: 0.4 (discard below this)

Include 10 test cases: 5 true causal sentences, 5 correlation-only sentences.
Strategy A should correctly classify all 10.
```

---

### Prompt 2.3 — Graph builder (Neo4j loader)

```
You are building the Neo4j graph builder for butterfly-effect.

Context:
- We have ExtractedEntity and ExtractedRelation objects
- Neo4j is running at NEO4J_URI with schema from db/schema.cypher
- We use the official neo4j Python driver (async)

Task: Create backend/butterfly/extraction/graph_builder.py

Requirements:
1. GraphBuilder class with async methods
2. async upsert_entity(entity: ExtractedEntity) -> str (node_id)
   - MERGE on entity name + label (don't create duplicates)
   - Update mention_count property on each upsert
   - Return the Neo4j internal node ID
3. async upsert_relation(relation: ExtractedRelation, source_event_id: str) -> str
   - MERGE on (source_node)-[r:RELATION_TYPE]->(target_node)
   - Update: mention_count, last_seen_at, evidence_path list
   - Return relationship ID
4. async link_event_to_entities(event_id: str, entity_ids: list[str])
   - Create (event)-[:MENTIONS]->(entity) for each
5. async get_causal_chain(start_entity_id: str, max_hops: int = 4) -> list[dict]
   - Cypher: MATCH path = (start)-[:CAUSES|TRIGGERS|INFLUENCES*1..{max_hops}]->(end)
   - Return nodes and relationships as dicts
   - Order by path length

6. Full pipeline method:
   async def process_event(event: Event) -> GraphBuildResult:
     - Extract entities
     - Extract relations
     - Upsert all to Neo4j
     - Return count of nodes + edges created

Include integration tests that run against a test Neo4j instance.
Test that upsert is truly idempotent (run twice, same result).
```

---

### Test 2 ✅

```bash
# Test the knowledge graph

# 1. Process some events manually
cd backend
python -c "
import asyncio
from butterfly.extraction.graph_builder import GraphBuilder
from butterfly.db.postgres import get_db

async def test():
    # Get 10 events from postgres
    # Process them through the pipeline
    # Query Neo4j for results
    pass

asyncio.run(test())
"

# 2. Query Neo4j directly
# Open http://localhost:7474 and run:
MATCH (n) RETURN labels(n), count(n)
# Expected: Event, Entity, Metric, Policy nodes exist

# 3. Test 3-hop query
MATCH path = (e:Event)-[:CAUSES|TRIGGERS|INFLUENCES*1..3]->(m:Metric)
RETURN path LIMIT 5
# Expected: At least 1 path found

# 4. Run all extraction tests
pytest tests/test_extraction/ -v

# PHASE 2 GATE: 3-hop query returns results, tests green → Phase 3
```

**Feedback to capture after Phase 2:**
- [ ] What entity types are most commonly extracted?
- [ ] Are relations being found or is the graph disconnected?
- [ ] Is the normalization catching Fed/FOMC/Federal Reserve correctly?
- [ ] What's the false positive rate on CORRELATES_WITH edges?

---

## PHASE 3 — Causal Core

**Duration:** 7 days
**Goal:** Working counterfactual diff on the 2022 Fed rate cycle
**Success metric:** Counterfactual delta for mortgage rates within ±20% of FRED's published data

This is the most critical phase. If this doesn't work, nothing else matters.

---

### Prompt 3.1 — pgmpy DAG builder

```
You are building the causal DAG builder for butterfly-effect.

Context:
- We have a Neo4j graph with CAUSES/TRIGGERS/INFLUENCES/CORRELATES_WITH relationships
- We need to build a pgmpy DAG from this graph for DoWhy to use
- Read CONTEXT.md section 9, Decision 2 carefully

Task: Create backend/butterfly/causal/dag.py

Requirements:
1. DAGBuilder class
2. async build_dag_for_event(event_id: str) -> pgmpy.models.BayesianNetwork
   - Query Neo4j: get all nodes/edges reachable from event_id within 4 hops
   - Filter: only use CAUSES and TRIGGERS edges (not CORRELATES_WITH)
   - Build pgmpy DAG: each node is an entity/metric, each CAUSES edge is a DAG edge
   - Validate: DAG must be acyclic (pgmpy raises if not)
   - If cycle detected: remove the weakest edge (lowest strength_score) and retry

3. export_dag_as_dict(dag) -> dict
   - For storage and caching: {nodes: list[str], edges: list[tuple]}

4. Caching:
   - Cache built DAGs in Redis with 1-hour TTL
   - Key: "dag:{event_id}"
   - Serialize with pickle (for now)

Important: pgmpy requires node names as strings. 
Use entity_id as the node name, not entity name (names have spaces/special chars).
Build a mapping dict: {entity_id: entity_name} for display purposes.

Test: Build DAG for seed data "Fed raises rates".
Assert: DAG contains nodes for Treasury, Mortgage, Housing, Employment.
Assert: DAG is acyclic.
```

---

### Prompt 3.2 — DoWhy causal identification

```
You are implementing DoWhy causal identification for butterfly-effect.

Context:
- We have a pgmpy DAG from dag.py
- We have time-series data for each metric node from FRED
- We want to estimate: "What is the causal effect of X on Y?"

Task: Create backend/butterfly/causal/identification.py

Requirements:
1. CausalIdentifier class
2. estimate_effect(
       dag: BayesianNetwork,
       treatment_node: str,       # e.g., "entity_fedfunds"
       outcome_node: str,          # e.g., "entity_mortgage30us"  
       data: pd.DataFrame          # time-series data with one col per node
   ) -> CausalEstimate

3. CausalEstimate dataclass:
   {
     treatment: str,
     outcome: str,
     ate: float,                  # Average Treatment Effect
     confidence_interval: tuple[float, float],
     identification_method: str,  # "backdoor" | "frontdoor" | "iv"
     estimator_used: str,
     refutation_results: dict,
     identified: bool             # False if DoWhy couldn't identify
   }

4. Implementation steps:
   a. Create dowhy.CausalModel(data, treatment, outcome, graph_dot_string)
   b. Identify effect (model.identify_effect())
   c. Estimate effect using LinearRegressionEstimator
   d. Run 3 refutation tests automatically:
      - refute_estimate("random_common_cause")
      - refute_estimate("placebo_treatment_refuter", placebo_type="permute")
      - refute_estimate("data_subset_refuter", subset_fraction=0.8)
   e. Mark identified=True only if all 3 refutations pass

5. If DoWhy cannot identify (no valid path): 
   - Return CausalEstimate with identified=False
   - Log warning with explanation
   - Do NOT raise — callers must handle identified=False

Use the FRED fixture data for 2022 (in tests/fixtures/fed_2022.json) as test input.
Assert that Fed → Mortgage effect is identified and ATE is positive.
```

---

### Prompt 3.3 — Counterfactual diff engine

```
You are building the counterfactual diff engine — the core of butterfly-effect.

Context:
- We can identify causal effects with DoWhy
- We need to run TWO simulations and subtract them
- Read CONTEXT.md Decision 4: we output relative change, not absolute prediction

Task: Create backend/butterfly/causal/counterfactual.py

Requirements:
1. CounterfactualEngine class

2. async run_counterfactual(
       event_id: str,
       horizon_hours: int = 168    # 1 week default
   ) -> CounterfactualResult

3. CounterfactualResult:
   {
     event_id: str,
     timeline_a: dict[str, list[float]],   # {metric_id: [values at t0, t1, ...t_n]}
     timeline_b: dict[str, list[float]],   # Same but counterfactual
     diff: dict[str, list[float]],         # A - B at each timestep
     causal_edges: list[CausalEdge],       # Validated edges with deltas
     peak_delta_at_hours: dict[str, float],# When does each effect peak?
     run_metadata: dict
   }

4. Timeline generation:
   Timeline A (event happens):
     - Get historical data for all metric nodes from FRED
     - Apply estimated causal effects from DoWhy at correct latency offsets
     - Propagate through the causal chain (topological order through DAG)
   
   Timeline B (counterfactual):
     - Same historical data
     - Do NOT apply causal effects
     - Just trend continuation from pre-event baseline

5. Diff calculation:
   - diff[metric][t] = timeline_a[metric][t] - timeline_b[metric][t]
   - Store peak delta time (argmax of abs(diff))

6. Convert results to CausalEdge objects with populated counterfactual_delta

Use the Fed 2022 fixture. 
Assert: mortgage rate shows positive delta (rates went up) in timeline_a.
Assert: timeline_b is flat relative to pre-event trend.
Assert: diff is non-zero for at least mortgage, housing, unemployment nodes.
```

---

### Test 3 ✅ — THE CRITICAL TEST

```bash
# This is the moment of truth. Does the causal inference work?

cd backend
python scripts/validate_fed_2022.py

# This script should:
# 1. Load the fed_2022.json fixture
# 2. Build the DAG
# 3. Run DoWhy identification
# 4. Run counterfactual engine
# 5. Print a table like:

# ┌─────────────────┬──────────┬──────────┬───────────┬──────────┐
# │ Metric          │ Our Δ    │ FRED Δ   │ Error     │ Pass?    │
# ├─────────────────┼──────────┼──────────┼───────────┼──────────┤
# │ Mortgage30US    │ +2.1%    │ +2.3%    │ 8.7%      │ ✅       │
# │ Housing Starts  │ -16.2%   │ -18.4%   │ 11.9%     │ ✅       │
# │ Unemployment    │ +0.3pp   │ +0.2pp   │ 50%       │ ❌       │
# └─────────────────┴──────────┴──────────┴───────────┴──────────┘
# Overall: 2/3 pass (≥20% error threshold)

# PHASE 3 GATE: At least 2/3 metrics within ±20% → proceed
# If gate fails: DO NOT PROCEED. Tune the DAG and re-run.
```

**Feedback to capture after Phase 3:**
- [ ] Which metrics passed/failed validation?
- [ ] What's the most common failure mode? (wrong DAG? wrong data? missing confounder?)
- [ ] Does the evidence path clearly explain why each edge exists?
- [ ] Is the 168-hour horizon right or should it be longer?

---

## PHASE 4 — Simulation Layer

**Duration:** 7 days
**Goal:** Mesa agent simulation that produces observable reactions to events
**Success metric:** 100-agent simulation completes in under 5 minutes with logged behavior

---

### Prompt 4.1 — Mesa agent definitions

```
You are building the agent simulation layer for butterfly-effect.

Context:
- Read CONTEXT.md Decision 1: agents must use empirically constrained reaction functions
- Do NOT use LLMs to generate agent reactions — use historical data
- We use Mesa 2.x for the ABM framework

Task: Create backend/butterfly/simulation/agents.py

Define these agent types (all extend mesa.Agent):

1. MarketAgent (represents institutional investors, funds)
   Properties: portfolio_exposure (0-1), risk_tolerance (0-1), sector_focus (str)
   Reaction function: 
   - On interest rate event: adjust portfolio_exposure by 
     -(rate_change * 0.6 * (1 - risk_tolerance)) with Gaussian noise (σ=0.05)
   - Source: Based on empirical data from Bernanke 2005 transmission mechanism paper
   
2. HousingAgent (represents real estate market participants)
   Properties: inventory_level (float), price_index (float), region (str)
   Reaction function:
   - On mortgage rate change: adjust inventory_level by 
     -(mortgage_delta * 2.3) with lag of 2 simulation steps
   - Source: NAR historical correlation data
   
3. SupplyChainAgent (represents manufacturers/suppliers)
   Properties: input_cost_index (float), output_capacity (float), supplier_count (int)
   Reaction function:
   - On energy/commodity price event: adjust output_capacity by
     -(price_delta * 0.4 * (1/supplier_count)) with lag of 3 steps
   
4. PolicyAgent (represents regulators, unchanged — observes only)
   Properties: mandate_metric (str), current_reading (float), target (float)
   Reaction: none (observer only, feeds back to causal graph)

Each agent must:
- Log every state change with: {agent_id, timestep, property, old_value, new_value, reason}
- This log is how we trace causal chains through agent behavior
- Include get_state() -> dict method

Include unit tests for each reaction function with known inputs/outputs.
```

---

### Prompt 4.2 — Mesa model + parallel runner

```
You are building the simulation model and parallel runner for butterfly-effect.

Context:
- We have agent types from agents.py
- We need to run TWO simultaneous simulations (Timeline A and B)
- Results feed into the counterfactual diff engine

Task: Create:

1. backend/butterfly/simulation/model.py — ButterflyModel(mesa.Model)
   - __init__(event: Event | None, n_market_agents: int, n_housing_agents: int, ...)
   - If event is None: this is Timeline B (counterfactual)
   - If event is provided: inject event signal at step 0 for Timeline A
   - step() method: advance all agents one timestep
   - get_snapshot() -> dict: current state of all agents
   - datacollector: Mesa DataCollector tracking portfolio_exposure, price_index, output_capacity

2. backend/butterfly/simulation/runner.py — SimulationRunner
   - async run_parallel(event: Event, steps: int = 168) -> SimulationResult
   - Runs Timeline A and B concurrently using asyncio
   - Each sim: ButterflyModel(event) and ButterflyModel(None)
   - Returns: SimulationResult{timeline_a_data, timeline_b_data, agent_logs}
   - Progress: emit progress events (for WebSocket updates later)

3. SimulationResult model (add to models/simulation.py):
   - timeline_a: dict[int, dict]   # step → agent state snapshot
   - timeline_b: dict[int, dict]
   - agent_logs: list[dict]         # all state change events
   - steps_completed: int
   - duration_seconds: float

Rules:
- Maximum 500 agents total (from CONTEXT.md config)
- Timeout after 300 seconds (from CONTEXT.md config)
- Log memory usage — simulation should stay under 512MB
- Include progress callback parameter for future WebSocket integration

Test: Run 100-agent simulation for 168 steps with the Fed 2022 event.
Assert: Completes in under 5 minutes.
Assert: agent_logs is non-empty.
Assert: Timeline A portfolio_exposure differs from Timeline B at step 50+.
```

---

### Test 4 ✅

```bash
cd backend
python scripts/run_test_simulation.py

# Expected output:
# Starting simulation: Timeline A (with event) + Timeline B (counterfactual)
# Agents: 100 (50 market, 30 housing, 20 supply chain)
# ...
# Simulation complete in 127.3s
# Timeline A final state: portfolio_exposure avg: 0.41 (baseline was 0.62)
# Timeline B final state: portfolio_exposure avg: 0.61 (minimal drift)
# Diff at peak (step 48): 0.21

pytest tests/test_simulation/ -v
# All green

# PHASE 4 GATE: Simulation completes <5 min, A != B → Phase 5
```

---

## PHASE 5 — API Layer

**Duration:** 5 days
**Goal:** Full REST API that orchestrates everything as async jobs
**Success metric:** Postman collection of 10 requests all return correct responses

---

### Prompt 5.1 — Full API implementation

```
You are building the REST API layer for butterfly-effect.

Context: See CONTEXT.md section 5 (API Contract) for all routes.

Task: Implement all API routes in backend/butterfly/api/

1. events.py — /api/v1/events
   POST /api/v1/events
     Body: {title, description, source, occurred_at, raw_text}
     Action: Save to postgres, trigger async NLP extraction + graph building
     Returns: {event_id, status: "processing"}
   
   GET /api/v1/events?page=1&limit=20&source=fred
     Returns paginated list with total count

   GET /api/v1/events/{event_id}
     Returns full event + processing status

2. causal.py — /api/v1/causal
   POST /api/v1/causal/analyze
     Body: {event_id, horizon_hours: 168}
     Action: Queue Celery job for full causal analysis
     Returns: {job_id, status: "queued"}
   
   GET /api/v1/causal/{event_id}
     Returns: full causal chain (DAG nodes + edges with all metadata)
   
   GET /api/v1/causal/{event_id}/diff
     Returns: timeline A, timeline B, diff data (for the frontend visualization)

3. simulation.py — /api/v1/simulation  
   POST /api/v1/simulation/run
     Body: {event_id, n_agents: 100, steps: 168}
     Action: Queue Celery job
     Returns: {run_id, status: "queued", estimated_seconds: 120}
   
   GET /api/v1/simulation/{run_id}
     Returns: SimulationResult or {status: "running", progress: 0.45}

Rules:
- All endpoints return JSON
- Use FastAPI background tasks for quick jobs, Celery for long jobs (>10s)
- All list endpoints: paginated with {items, total, page, pages}
- All error responses: {error: str, detail: str, code: int}
- Add OpenAPI tags and descriptions so the auto-docs are actually useful
- Rate limit: 10 requests/min per IP for simulation endpoints (use slowapi)

Create Postman collection export at docs/butterfly-api.postman_collection.json
```

---

### Test 5 ✅

```bash
# Start everything
docker compose up -d
cd backend && uvicorn butterfly.main:app --reload

# Test with httpie or curl
http POST localhost:8000/api/v1/events \
  title="Fed raises rates 75bps" \
  description="FOMC decision June 2022" \
  source="manual" \
  occurred_at="2022-06-15T14:00:00Z" \
  raw_text="The Federal Reserve raised its benchmark interest rate..."

# Should return: {"event_id": "...", "status": "processing"}

# Import Postman collection and run all 10 requests
# All must return 2xx

# PHASE 5 GATE: All API endpoints working, Postman green → Phase 6
```

---

## PHASE 6 — Frontend

**Duration:** 7 days
**Goal:** A beautiful, functional dashboard that makes the causal chain visible
**Success metric:** Load demo data → see causal ripple map → scrub through time → see evidence

---

### Prompt 6.1 — Dashboard layout

```
You are building the Next.js frontend for butterfly-effect.

Context:
- Next.js 14 App Router, TypeScript strict, Tailwind, shadcn/ui
- Backend API at http://localhost:8000
- This is an open-source project that needs to look impressive on GitHub

Task: Create the main dashboard (app/page.tsx and supporting components)

The dashboard has 3 panels:
1. Left sidebar (240px): Event list
   - Shows recent events from /api/v1/events
   - Each item: source badge, title, relative time
   - Click to load that event's causal analysis
   - "Add Event" button at bottom (opens a modal form)
   - EventInput.tsx component

2. Main area: Causal graph (Sigma.js)
   - Full height, fills remaining space
   - Shows the causal chain as a force-directed graph
   - Nodes: colored by type (Event=purple, Metric=teal, Entity=coral)
   - Edges: width proportional to strength_score, color by confidence
   - Hover on edge: show strength + confidence + latency
   - Click on node: open evidence panel
   - CausalGraph.tsx component

3. Right panel (320px, collapsible): Evidence panel
   - Shows when a node is selected
   - Title: node name + type
   - Causal edges in/out with strength scores
   - Evidence path: clickable source links
   - Counterfactual delta badge: "+2.1% vs baseline"
   - EvidencePanel.tsx component

4. Bottom bar: Temporal scrubber
   - D3 timeline from t=0 to t=168h
   - Draggable handle
   - As user drags: graph updates to show cascade state at that time
   - Shows "Timeline A" vs "Timeline B" toggle
   - TemporalScrubber.tsx component

Design requirements:
- Dark theme preferred (most dev tools use dark theme = viral on GitHub)
- Dense information display but not cluttered
- The graph should look beautiful and immediately impressive in a screenshot
- Loading states for all async operations

Create a DEMO MODE that loads the Fed 2022 fixture data locally
(no backend needed for demo mode — hardcoded fixture in lib/demo-data.ts)
```

---

### Prompt 6.2 — Counterfactual diff view

```
You are building the CounterfactualDiff component for butterfly-effect.

Context:
- User clicks "Show Counterfactual" button in the dashboard
- We need to show Timeline A vs Timeline B side by side
- Data comes from GET /api/v1/causal/{event_id}/diff

Task: Create frontend/components/CounterfactualDiff.tsx

The component shows:
1. Header row: "With Event" vs "Without Event" column labels
2. For each tracked metric (mortgage rate, housing starts, etc.):
   - Metric name + icon
   - Mini sparkline chart (Timeline A in amber, Timeline B in gray)
   - Delta badge: "+2.1%" (positive = red if bad, green if good, relative to context)
   - Confidence bar showing the 95% CI width
   - "View evidence" link

3. Summary card at bottom:
   - "This event caused X metrics to deviate significantly"
   - "Peak effect observed at T+48 hours"
   - "Causal chain: 4 hops (Fed → Treasury → Mortgage → Housing)"

Use Recharts for the sparklines (already in stack).
Animate the diff appearing: lines draw from left to right on mount.
Mobile responsive (stack vertically on <768px).

Props:
interface CounterfactualDiffProps {
  diffData: DiffResult;  // from API
  eventTitle: string;
}

Include Vitest unit test with mock data.
```

---

### Test 6 ✅

```bash
cd frontend
npm run dev

# Open http://localhost:3000
# Click "Demo Mode" button

# Check list:
# [ ] Event list loads in sidebar
# [ ] Causal graph renders (nodes and edges visible)
# [ ] Hover on edge shows tooltip with strength/confidence
# [ ] Click a node opens evidence panel
# [ ] Temporal scrubber moves smoothly
# [ ] Counterfactual diff shows two lines per metric
# [ ] "Add Event" modal opens and submits

# Screenshot the graph — it should look impressive
# Post screenshot in project notes for feedback

npm run type-check  # No TypeScript errors
npm run test        # All Vitest tests green

# PHASE 6 GATE: Demo mode works fully without backend → Phase 7
```

---

## PHASE 7 — Validation

**Duration:** 5 days
**Goal:** Prove the causal inference actually works on historical data
**Success metric:** 2 out of 3 historical scenarios pass the ±20% accuracy threshold

---

### Prompt 7.1 — Validation framework

```
You are building the validation framework for butterfly-effect.

Context:
- We claim to do causal inference, not correlation
- We must prove this works before launching publicly
- See CONTEXT.md section 8 (Validation Tests) and VALIDATION.md

Task: Create backend/tests/validation/

1. Create tests/validation/conftest.py
   - Load all fixtures (fed_2022.json, texas_storm_2021.json, covid_supply_chain.json)
   - Ground truth: published consensus estimates for each event's effects
   - Tolerance: ±20% from ground truth to pass

2. Create validate_fed_2022.py
   Scenario: FOMC June 2022, 75bps hike
   Ground truth (from Fed + CBO published estimates):
   - 30yr mortgage rate: +2.1% over next 90 days (we saw +1.94% actual)
   - Housing starts: -16% over next 6 months
   - Unemployment: +0.2pp over next 12 months
   Test: Run our counterfactual engine on the fixture data
   Assert: Our estimates within ±20% of ground truth for each metric

3. Create validate_texas_storm.py
   Scenario: ERCOT grid failure February 2021
   Ground truth (from Texas Legislature post-mortem):
   - Natural gas prices: +800% peak (3-day)
   - Manufacturing output: -35% week 1
   - Insurance claims: $200B+
   Test: Does our causal chain correctly show the energy → manufacturing path?
   Assert: At least 3-hop chain found: grid failure → energy price → manufacturing → employment

4. Create validate_covid_supply.py
   Scenario: Semiconductor shortage 2021
   Ground truth (well-documented in academic literature):
   - Auto production: -25% 
   - Used car prices: +30%
   - CPI: +0.4pp contribution
   Test: Does the chain reach from shortage → auto → used cars → CPI?

5. Create a validation report generator:
   python scripts/run_validation.py
   Outputs a markdown report: docs/VALIDATION_RESULTS.md
   Shows pass/fail per scenario, error percentages, and recommendations

Requirement: At least 2/3 scenarios must pass. If not, DO NOT move to Phase 8.
Instead: file issues, tune the DAG structure, and re-run.
```

---

### Test 7 ✅

```bash
cd backend
python scripts/run_validation.py

# Expected output:
# butterfly-effect Validation Report
# ===================================
# Scenario 1: 2022 Fed Rate Cycle
#   Mortgage rate delta: PASS (error: 8.7%)
#   Housing starts delta: PASS (error: 11.2%)  
#   Unemployment delta: FAIL (error: 34%) ← needs work
#   Result: 2/3 metrics pass ✅
#
# Scenario 2: 2021 Texas Winter Storm
#   3-hop chain found: ✅
#   Energy price direction: PASS
#   Manufacturing direction: PASS
#   Result: PASS ✅
#
# Scenario 3: COVID Supply Chain
#   Chain depth ≥3: ✅
#   Auto production direction: PASS
#   CPI attribution: FAIL (too noisy)
#   Result: 1/3 metrics pass ❌
#
# Overall: 2/3 scenarios pass → PROCEED TO PHASE 8

# PHASE 7 GATE: 2/3 scenarios pass → Phase 8 (Launch)
```

---

## PHASE 8 — Launch

**Duration:** 3 days
**Goal:** Go public. Get GitHub stars. Make it viral.
**Success metric:** 100 GitHub stars in first week

---

### Prompt 8.1 — Demo mode polish

```
You are making butterfly-effect demo-ready for GitHub launch.

Task: Polish the demo experience

1. Create app/demo/page.tsx
   - Loads ENTIRELY from local fixture data (no backend needed)
   - Shows all 3 historical scenarios as tabs:
     "2022 Fed Hike" | "2021 Texas Storm" | "COVID Supply Chain"
   - Each tab: full causal graph + counterfactual diff pre-loaded
   - "Deploy your own" button linking to README

2. Add a banner to the main UI:
   "🦋 Demo mode — using pre-loaded 2022 Fed rate cycle data"
   "Connect your own data sources in Settings"

3. Create a GIF/video recording script (instructions only):
   - Instruction file: docs/RECORDING.md
   - Steps to record a 30-second demo GIF showing:
     1. Load the demo event
     2. Watch graph appear
     3. Scrub the temporal slider
     4. Click counterfactual diff
     5. View evidence panel
   - Tool recommendation: Kap (macOS) or Peek (Linux)

4. Ensure docker compose up works cleanly on:
   - macOS (Apple Silicon)
   - macOS (Intel)
   - Ubuntu 22.04
   - Windows 11 (WSL2)
   - Add OS-specific notes to README if needed
```

---

### Prompt 8.2 — GitHub launch materials

```
You are preparing butterfly-effect for maximum GitHub impact.

Task: Create all GitHub-facing materials

1. Update README.md
   - Add a demo GIF at the top (placeholder: "Demo GIF coming soon")
   - Add "Quick Start in 3 commands" section right after the demo GIF
   - Add "⭐ Star this repo if you find it useful" near the top
   - Add contributor badges + "Built with" section

2. Create CONTRIBUTING.md
   - How to set up dev environment (step by step)
   - How to run tests
   - PR process
   - "Good first issue" labels explained
   - Code of conduct link

3. Create .github/ISSUE_TEMPLATE/
   - bug_report.md
   - feature_request.md
   - validation_failure.md (specific to our use case — report when causal estimate is wrong)

4. Create .github/workflows/ci.yml
   - Trigger: push + PR to main
   - Jobs:
     a. lint: ruff check + mypy
     b. test-backend: pytest with coverage report
     c. test-frontend: npm run type-check + vitest
     d. docker-build: docker compose build (smoke test)
   - Badge: add CI badge to README

5. Create initial GitHub issues (as markdown files in docs/issues/):
   - "Add NewsAPI ingester" (good first issue)
   - "Add synthetic control validation method" (medium)
   - "Build agent memory persistence with Mem0" (medium)
   - "Add real-time WebSocket progress for simulations" (advanced)
   - "Add export to PDF report" (medium)

6. Write a launch post (docs/LAUNCH_POST.md):
   - For: Hacker News (Show HN)
   - Format: "Show HN: butterfly-effect — causal chain tracing for policy and market shocks"
   - Include: what it does, how it works (one paragraph each), link to demo
   - Length: under 500 words
   - Tone: technical, honest about limitations, open to feedback
```

---

### Test 8 ✅ — LAUNCH CHECK

```bash
# Final pre-launch checklist

# 1. Clean install test
rm -rf backend/venv node_modules
git clone <repo> butterfly-effect-test
cd butterfly-effect-test
docker compose up -d
cd backend && pip install -r requirements.txt && uvicorn butterfly.main:app
cd frontend && npm install && npm run dev
# Both must work without errors

# 2. CI passes
git push origin main
# Check GitHub Actions: all jobs green

# 3. Demo loads
open http://localhost:3000/demo
# Full causal graph loads, scrubber works, counterfactual diff shows

# 4. Validation passes
cd backend && python scripts/run_validation.py
# 2/3 scenarios pass

# 5. README renders correctly on GitHub
# Preview at https://github.com/Om7035/butterfly-effect

# LAUNCH: Post to HN, Reddit r/MachineLearning, Twitter/X
# Target: 100 stars in week 1
```

---

## Post-Launch Iteration Backlog

After launch, use this framework for each new feature:

```
Week N+1: Listen
  - Monitor GitHub issues + HN comments
  - Note top 3 requested features

Week N+2: Pick + Build
  - Pick 1 feature from the top 3
  - Build it in under 5 days
  - Ship it

Week N+3: Announce
  - Tweet/post about the new feature
  - Link back to the GitHub repo
  - Repeat
```

### Likely first post-launch features (based on expected demand):
1. **NewsAPI ingester** (most requested — people want real-time)
2. **Export to report PDF** (enterprise users need to present findings)
3. **Mem0 agent memory** (replace Zep — open source, self-hosted)
4. **WebSocket simulation progress** (UX improvement)
5. **Custom DAG editor** (let users define their own causal structure)

---

*PHASES.md — butterfly-effect*
*Last updated: 2026-03-29*
*Follow the Experimental Builder Framework: ship ugly, fix it, repeat.*