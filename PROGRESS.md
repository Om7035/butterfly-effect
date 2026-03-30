# butterfly-effect — Build Progress

## Phase Status

| Phase | Name | Status | Gate |
|-------|------|--------|------|
| 0 | Scaffolding | COMPLETE | `GET /health` returns 200 |
| 1 | Data Pipeline | COMPLETE | 50+ events ingested, tests green |
| 2 | Knowledge Graph | COMPLETE | 3-hop queries work, tests green |
| 3 | Causal Core | COMPLETE | 3/3 metrics within +/-20% of ground truth |
| 4 | Simulation | COMPLETE | 4/4 gate checks pass, 0.2s for 100 agents/168 steps |
| 5 | API Layer | COMPLETE | All routes wired, Postman collection created |
| 6 | Frontend | COMPLETE | Dashboard + demo page, TypeScript clean |
| 7 | Validation | planned | |
| 8 | Launch | planned | |

## Phase 3 Validation Results (Fed 2022)

```
Metric               Our D    Truth D      Error    Pass?
------------------------------------------------------------
MORTGAGE30US        +1.950     +1.930       1.0%     PASS
HOUST             -254.281   -247.000       2.9%     PASS
UNRATE              +0.246     +0.230       7.0%     PASS
------------------------------------------------------------
Result: 3/3 metrics within +/-20% of ground truth
Causal chain depth: 10 edges PASS (need >=3)
PHASE 3 GATE PASSED
```

## Test Suite

```
18 passed in 2.68s
- tests/test_causal/   (9 tests)
- tests/test_ingestion/ (4 tests)
- tests/test_api/       (1 test)
- tests/test_extraction/ (4 tests — require spaCy model)
```

## Quick Start

```bash
# Start Docker services
docker compose up -d

# Install deps (venv already exists)
cd backend
venv\Scripts\python.exe -m pip install -r requirements.txt

# Run API
venv\Scripts\uvicorn.exe butterfly.main:app --reload

# Run tests
venv\Scripts\python.exe -m pytest tests/test_causal/ tests/test_ingestion/ tests/test_api/ -v

# Run Phase 3 validation
venv\Scripts\python.exe scripts/validate_fed_2022.py
```

## Key Files

```
backend/butterfly/
  causal/
    dag.py              # pgmpy DAG builder from Neo4j graph
    identification.py   # DoWhy / OLS causal identification
    counterfactual.py   # Timeline A vs B diff engine
  models/
    causal_edge.py      # CausalEdge, CounterfactualResult models
  api/
    causal.py           # /api/v1/causal/* routes
backend/scripts/
  validate_fed_2022.py  # Phase 3 gate validation script
```

## Phase 4 Simulation Results

```
Simulation complete in 0.2s
Steps completed: 168
Agent log entries: 80

Timeline A final portfolio_exposure: 0.3686
Timeline B final portfolio_exposure: 0.6000
Diff at final step: 0.2314

  PASS  Completes in <5 min
  PASS  agent_logs non-empty
  PASS  Timeline A != Timeline B
  PASS  Steps completed = 168

4/4 checks passed — PHASE 4 GATE PASSED
```

## New Files (Phase 4)

```
backend/butterfly/
  simulation/
    agents.py       # MarketAgent, HousingAgent, SupplyChainAgent, PolicyAgent
    model.py        # ButterflyModel (Mesa Model)
    runner.py       # SimulationRunner (parallel A/B)
  models/
    simulation.py   # SimulationRun, SimulationResult models
  api/
    simulation.py   # /api/v1/simulation/* routes
backend/scripts/
  run_test_simulation.py  # Phase 4 gate script
backend/tests/test_simulation/
  test_agents.py    # 6 agent reaction tests
  test_runner.py    # 3 runner tests
```
