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
| 7 | Validation | COMPLETE | 3/3 scenarios pass, Phase 7 gate passed |
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

## Phase 7 Validation Results

```
Scenario 1: 2022 Fed Rate Cycle
  PASS  MORTGAGE30US: error 1.3%
  PASS  HOUST: error 2.6%
  PASS  UNRATE: error 6.7%
  PASS  chain_depth: 10 edges
  Result: 4/4 -- PASS

Scenario 2: 2021 Texas Winter Storm
  PASS  natgas_direction: peak +20.01
  PASS  manufacturing_direction: peak -0.26
  PASS  chain_depth: 3 edges
  Result: 3/3 -- PASS

Scenario 3: COVID Supply Chain Shock
  PASS  auto_production_direction: peak -25.51
  PASS  chain_depth: 3 edges
  PASS  cascade: 3 nonzero metrics
  Result: 3/3 -- PASS

Overall: 3/3 scenarios passed -- PHASE 7 GATE PASSED
```

## UI Improvements (Phase 6 overhaul)

- CausalGraph: force-directed layout, animated particles on edges, glowing nodes,
  pulsing selection ring, hover effects, edge latency labels
- TemporalScrubber: active effects strip, gradient fill, smooth drag handle
- EvidencePanel: confidence gradient bar, causal chain cards, evidence source list
- CounterfactualDiff: AreaChart with gradients, metric icons, delta bars
- EventSidebar: polished cards, animated active indicator
- globals.css: custom scrollbar, dark base, canvas transition fix


## Phase 8: Graph UI Redesign (Miro/Figjam Style)

**Status:** ✅ COMPLETE

**Goal:** Transform Sigma.js force-directed graph into Miro/Figjam-style infinite canvas

### Implementation Summary

**New Components Created:**
- `frontend/components/graph/CausalGraphCanvas.tsx` - Main React Flow wrapper
- `frontend/components/graph/nodes/EventNode.tsx` - Sticky note style (yellow gradient)
- `frontend/components/graph/nodes/EntityNode.tsx` - Card style (blue gradient)
- `frontend/components/graph/nodes/MetricNode.tsx` - Chart style (green gradient)
- `frontend/components/graph/nodes/PolicyNode.tsx` - Badge style (purple gradient)
- `frontend/components/graph/edges/CausalEdge.tsx` - Smooth bezier with animations
- `frontend/components/graph/edges/InfluenceEdge.tsx` - Dashed influence edges
- `frontend/components/graph/controls/GraphToolbar.tsx` - Layout controls
- `frontend/components/graph/controls/LayoutSelector.tsx` - Layout picker
- `frontend/components/graph/utils/graphTransforms.ts` - Data transforms & layouts
- `frontend/components/CausalGraphNew.tsx` - New graph component
- `frontend/app/graph-demo/page.tsx` - Demo page with sample data

**Technology Migration:**
- ❌ Sigma.js (canvas-based, force-directed only)
- ✅ React Flow (React components, freeform positioning)

**Features Implemented:**
- ✅ Freeform drag-and-drop positioning
- ✅ Smooth bezier edges (hand-drawn aesthetic)
- ✅ Animated flow particles on causal edges
- ✅ Confidence-based edge coloring
- ✅ Latency labels on edges
- ✅ Built-in minimap
- ✅ Zoom/pan controls
- ✅ 4 layout algorithms (hierarchical, radial, grid, freeform)
- ✅ Miro-inspired color palette
- ✅ Sticky note aesthetic for event nodes
- ✅ Card style for entity nodes
- ✅ Chart style for metric nodes
- ✅ Badge style for policy nodes
- ✅ Hover effects and animations
- ✅ Confidence score bars
- ✅ Delta indicators (↑ ↓)

**Visual Design:**
- Soft, rounded shapes with subtle shadows
- Pastel gradients (yellow, blue, green, purple)
- Whiteboard/canvas feel (#F5F5F5 background)
- Hand-drawn bezier connectors
- Depth through layering

**Demo:**
Visit `/graph-demo` to see the new Miro-style graph in action

**Next Steps:**
- [ ] Replace old CausalGraph.tsx with CausalGraphNew.tsx
- [ ] Add node palette for drag-to-add
- [ ] Implement multi-select with lasso
- [ ] Add keyboard shortcuts
- [ ] Optimize for mobile/touch

**Files Modified:**
- `frontend/package.json` - Added reactflow dependency
- `PROGRESS.md` - This update

**Documentation:**
- `docs/GRAPH_UI_REDESIGN.md` - Complete design specification
- `frontend/components/graph/README.md` - Component documentation
- `CODEBASE_ANALYSIS.md` - Updated with graph UI section

---

*Phase 8 completed: March 30, 2026*
