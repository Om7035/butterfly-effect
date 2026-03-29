# 🦋 butterfly-effect

> **A causal inference engine that makes invisible cascade effects visible, traceable, and quantifiable.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-blue.svg)](https://neo4j.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Stars](https://img.shields.io/github/stars/Om7035/butterfly-effect?style=social)](https://github.com/Om7035/butterfly-effect)

---

```
"It used to be thought that the events that changed the world were things like
big bombs, maniac politicians, huge earthquakes, or vast population movements,
but it has been realized that this is a very old-fashioned view held by people
totally out of touch with modern thought. The things that change the world,
according to Chaos theory, are the tiny things. A butterfly flaps its wings
in the Amazonian jungle, and subsequently a storm ravages half of Europe."
                                                          — Terry Pratchett
```

---

## 🧭 What is butterfly-effect?

Most analytical tools answer **"what happened?"**
Some answer **"what will happen?"**

**butterfly-effect** answers the question nobody else does:

> *"This event just happened. What else will it affect — that nobody is talking about yet — and how do we prove it?"*

It is a **causal chain tracing system** that:

1. **Ingests** real-world signals — policy docs, news feeds, SEC filings, macro data
2. **Builds** a knowledge graph of causal relationships between entities
3. **Simulates** two parallel timelines: one where the event happens, one where it doesn't
4. **Diffs** those timelines to isolate true causal impact (not correlation)
5. **Visualizes** the cascade as an interactive ripple map with confidence scores

Unlike prediction markets (which show *what* might happen) or dashboards (which show *what is* happening), butterfly-effect shows **how effects propagate** — the chain, not just the outcome.

---

## 🎯 The Core Problem

Humans think linearly. Complex systems behave like networks.

```
Human model:     Fed raises rates → bond prices fall

Reality:         Fed raises rates
                      │
                      ├──▶ Bond prices fall
                      │         │
                      │         └──▶ Pension fund rebalancing
                      │                   │
                      │                   └──▶ Equity selloff in tech
                      │                              │
                      ├──▶ Mortgage rates spike       └──▶ VC dry powder shrinks
                      │         │                              │
                      │         └──▶ Housing starts drop       └──▶ Startup layoffs
                      │                   │                              │
                      │                   └──▶ Construction jobs fall    └──▶ Consumer spending dips
                      │
                      └──▶ Dollar strengthens
                                │
                                └──▶ Emerging market debt crisis (6 months later)
```

By the time the last effects are visible, the opportunity window has closed.
**butterfly-effect makes the full chain visible at t=0.**

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🕸️ **Causal Graph Engine** | Neo4j-backed knowledge graph with typed, weighted, time-stamped causal edges |
| ⚖️ **Counterfactual Diff** | Run two parallel simulations (event vs. no-event) and subtract to isolate true impact |
| 📊 **Confidence Scoring** | Every causal edge gets a confidence interval backed by DoWhy identification tests |
| ⏱️ **Temporal Scrubber** | Slide through time to watch cascade propagation at any moment |
| 🔍 **Evidence Paths** | Every conclusion links to its source data — no black boxes |
| 🧪 **Refutation Testing** | Automated placebo + random-cause tests to reject spurious correlations |
| 📡 **Auto-Ingestion** | Continuous polling of FRED, SEC EDGAR, GDELT, NewsAPI — no manual uploads |
| 🤖 **Agent Simulation** | Mesa-powered multi-agent system with empirically constrained reaction functions |

---

## 🗺️ System Architecture

<div align="center">

| 📡 Data Ingestion | 🤖 NLP Extraction | 🕸️ Knowledge Graph |
| :--- | :--- | :--- |
| **FRED API** · Macro Data | **spaCy NER** · Transformers | **Neo4j** · Causal Nodes |
| **SEC EDGAR** · Filings | **Relationship** · Extraction | **Causal Edge** · Weighted |
| **GDELT** · Global Events | **Event Schema** · Normalization | **Evidence** · Traceable |
| **NewsAPI** · Real-time Feed | **Normalization** · Entity Mapping | **Schema** · Strength & Latency |

<br/>

| ⚖️ Parallel Simulation | 🧠 Causal Inference | 📊 Visualization |
| :--- | :--- | :--- |
| **Timeline A** · Event Happens | **DoWhy** · Identification | **Sigma.js** · Ripple Map |
| **Timeline B** · Counterfactual | **pgmpy** · DAG Building | **Cytoscape** · Causal Graph |
| **Mesa** · Agent Engine | **Refutation** · Testing | **D3.js** · Time Scrubber |
| **Mesa** · Reaction Functions | **Estimator** · Delta Calculation | **Next.js** · Dashboard UI |

</div>

<br/>

## 🔬 How the Counterfactual Engine Works

**Butterfly Effect** computes the **Causal Impact** by running two simultaneous, empirically-constrained simulations of the world.

### ⚖️ The Parallel Split
| Step | 🍏 Timeline A (Event Occurs) | 🍎 Timeline B (Counterfactual) |
| :--- | :--- | :--- |
| **t=0h** | **Signal Received** · Agents respond | **Baseline** · Pure noise/trend |
| **t=6h** | **Bond Mkts React** · Yield shift | **Flat** · Standard volatility |
| **t=24h** | **Equity Volatility** · Tech selloff | **Flat** · No signal |
| **t=72h** | **Mortgage Movement** · Rates up | **Standard** · No policy shift |
| **t=168h** | **Labor Signal** · Hiring freeze | **Baseline** · Trend continuation |

### 🧠 The Inference Output
Once simulations complete, the **Diff Engine** isolates the delta (`A - B`) and projects the **Causal Chain**:

> **Fed decision** (0.92) ➔ **Treasury yield** (0.78) ➔ **Mortgage rate** (0.71) ➔ **Housing starts** (0.54) ➔ **Labor signal**

*   **Strength Labels**: Numbers in parentheses represent normalized causal strength.
*   **Traceability**: Every arrow links to its primary source evidence path.

---

## 🧱 Causal Edge Schema

Every relationship in the knowledge graph is stored as a **Causal Edge**:

```json
{
  "edge_id": "causal_fed_mortgage_001",
  "source_node_id": "event_fed_rate_hike_jun2022",
  "target_node_id": "metric_30yr_mortgage_rate",
  "relationship_type": "influences_price",
  "strength_score": 0.78,
  "time_decay_factor": 0.12,
  "latency_hours": 48,
  "counterfactual_delta": 0.41,
  "confidence_interval": [0.71, 0.85],
  "evidence_path": [
    "fred_series_MORTGAGE30US",
    "fomc_statement_jun2022",
    "academic_paper_bernanke_2015"
  ],
  "refutation_passed": true,
  "created_at": "2026-03-29T10:00:00Z"
}
```

---

## 💼 Use Cases

### 🏛️ Government & Policy
**Problem:** A new energy subsidy is announced. What sectors will be affected in 6 months that nobody is discussing?

**Butterfly:** Traces the cascade from subsidy announcement → energy company capex → supplier hiring → regional housing → municipal tax base → public services. Shows decision makers the full second and third-order impact map *before* the bill passes.

---

### 📈 Hedge Funds & Asset Managers
**Problem:** The Fed just signaled rate changes. Show me second and third-order effects across asset classes.

**Butterfly:** Maps the causal chain from rate signal → bond repricing → equity rotations → sector exposures → credit spreads → emerging market spillovers. Timestamped so you know *when* each effect typically manifests.

---

### 🏢 Corporate Strategy (Fortune 500)
**Problem:** Our competitor just announced a merger. What's the cascade effect on our supply chain?

**Butterfly:** Traces from merger announcement → combined purchasing power → supplier contract renegotiations → your Tier-2 suppliers → your input cost structure → your margin exposure. Identifies which suppliers to call *today*.

---

### 🛡️ Risk Management & Insurance
**Problem:** This geopolitical event occurred. What are the cascading risks we should price in?

**Butterfly:** Builds the causal graph from geopolitical shock → commodity exposure → logistics routes → insured asset portfolios. Generates confidence-weighted risk exposure report with evidence paths.

---

### 🔬 Academic Research
**Problem:** I want to publish a rigorous causal analysis of how policy X affected outcome Y.

**Butterfly:** Provides DoWhy-backed causal identification with synthetic control counterfactuals. Every claim is falsifiable. Every edge links to its evidence. Generates publication-ready causal graphs.

---

## 🛠️ Tech Stack

<div align="center">

| 💻 Frontend | ⚙️ Backend | 🕸️ Knowledge Graph |
| :--- | :--- | :--- |
| **Next.js 14** · App Router | **FastAPI** · Async Python | **Neo4j 5.x** · Community |
| **Tailwind CSS** · Styling | **Celery** · Async Tasks | **GraphRAG** · Extractions |
| **Sigma.js** · Graph Visuals | **Redis** · Broker & Cache | **Causal Schema** · Custom |
| **D3.js** · Time Scrubber | **PostgreSQL** · Relational | **Cypher** · Graph Queries |

<br/>

| 🤖 Causal Core | ⚖️ Simulation | 📡 Data & Infra |
| :--- | :--- | :--- |
| **DoWhy** · Inference Engine | **Mesa** · ABM Framework | **FRED / SEC** · APIs |
| **pgmpy** · DAG Modeling | **LangGraph** · Optional LLM | **GDELT / News** · Streams |
| **causalml** · Hetero effects | **Reaction Functions** · Empirical | **Docker Compose** · Dev |
| **statsmodels** · Metrics | **Behavioral Logs** · Traceable | **Git Actions** · CI/CD |

</div>

<br/>

---

## 🚀 Quickstart

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- Neo4j (via Docker)

### 1. Clone the repo

```bash
git clone https://github.com/Om7035/butterfly-effect.git
cd butterfly-effect
```

### 2. Start infrastructure

```bash
docker compose up -d  # Starts Neo4j, Redis, PostgreSQL
```

### 3. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env     # Fill in API keys
python -m butterfly.db.init  # Initialize Neo4j schema
uvicorn butterfly.main:app --reload
```

### 4. Frontend setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

### 5. Run your first analysis

Open `http://localhost:3000` and click **"Run Demo: 2022 Fed Rate Cycle"**

---

## 📁 Project Structure

```
butterfly-effect/
├── README.md
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── butterfly/
│   │   ├── main.py                  # FastAPI app entry
│   │   ├── config.py                # Settings + env vars
│   │   ├── db/
│   │   │   ├── neo4j.py             # Graph DB connection
│   │   │   ├── postgres.py          # Relational DB
│   │   │   └── schema.cypher        # Neo4j schema init
│   │   ├── ingestion/
│   │   │   ├── fred.py              # FRED API poller
│   │   │   ├── edgar.py             # SEC EDGAR poller
│   │   │   ├── gdelt.py             # GDELT poller
│   │   │   ├── news.py              # NewsAPI poller
│   │   │   └── scheduler.py         # Celery beat tasks
│   │   ├── extraction/
│   │   │   ├── ner.py               # spaCy NER pipeline
│   │   │   ├── relations.py         # Relationship extraction
│   │   │   └── graph_builder.py     # Entity → Neo4j loader
│   │   ├── causal/
│   │   │   ├── dag.py               # pgmpy DAG builder
│   │   │   ├── identification.py    # DoWhy identification
│   │   │   ├── estimation.py        # Effect size estimation
│   │   │   ├── refutation.py        # Automated refutation tests
│   │   │   └── counterfactual.py    # Timeline A/B diff engine
│   │   ├── simulation/
│   │   │   ├── agents.py            # Mesa agent definitions
│   │   │   ├── model.py             # ABM model
│   │   │   └── runner.py            # Parallel simulation runner
│   │   ├── api/
│   │   │   ├── events.py            # Event endpoints
│   │   │   ├── causal.py            # Causal chain endpoints
│   │   │   ├── simulation.py        # Simulation endpoints
│   │   │   └── health.py            # Health check
│   │   └── worker.py                # Celery worker
│   ├── tests/
│   │   ├── test_ingestion.py
│   │   ├── test_causal.py
│   │   ├── test_simulation.py
│   │   └── fixtures/
│   │       └── fed_2022_fixture.json
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Home / dashboard
│   │   ├── analysis/[id]/page.tsx   # Causal chain viewer
│   │   └── demo/page.tsx            # Demo mode
│   ├── components/
│   │   ├── CausalGraph.tsx          # Sigma.js ripple map
│   │   ├── TemporalScrubber.tsx     # D3 time slider
│   │   ├── EvidencePanel.tsx        # Source trail panel
│   │   ├── CounterfactualDiff.tsx   # A/B timeline view
│   │   └── ConfidenceBar.tsx        # Confidence indicator
│   └── lib/
│       ├── api.ts                   # Backend API client
│       └── graph.ts                 # Graph utilities
│
└── docs/
    ├── CONTEXT.md                   # AI IDE context file
    ├── PHASES.md                    # Build phase plan
    ├── ARCHITECTURE.md              # Deep architecture docs
    └── VALIDATION.md                # Backtesting methodology
```

---

## 🧪 Validation Methodology

**Butterfly Effect** uses a 4-layer validation stack to ensure causal claims are not just correlations:

### 🛡️ Layer 1: DoWhy Identification
*   **DAG Pathing**: Can we identify a valid causal path in the directed acyclic graph?
*   **Confounder Guard**: Are backdoor paths successfully blocked by observed variables?

### 🧪 Layer 2: Automated Refutation
*   **Placebo Test**: Does the effect disappear when we use a fake cause?
*   **Noise Test**: Does adding random common causes change our estimate?
*   **Stability Test**: Is the estimate consistent across different data subsets?

### 📜 Layer 3: Historical Backtesting
*   **Benchmarking**: Run against 10 historical events with known outcomes.
*   **Accuracy Check**: Compare counterfactual delta to published consensus (±20% threshold).

### 📐 Layer 4: Synthetic Control
*   **Weighted Controls**: For policy events, construct a weighted synthetic control group.
*   **Academic Rigor**: Compare outputs to `SyntheticControl` library standards.

---

## 🤝 Contributing

This project is in active development. Contributions are welcome.

```bash
# 1. Fork the repo
# 2. Create your feature branch
git checkout -b feature/your-feature-name

# 3. Make changes and test
pytest backend/tests/

# 4. Commit with conventional commits
git commit -m "feat: add granger causality validator"

# 5. Push and open a PR
git push origin feature/your-feature-name
```

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

---

## 📬 Contact

Built by **Om Kawale** — GitHub: [@Om7035](https://github.com/Om7035)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>butterfly-effect</strong> — making the invisible visible.<br/>
  If a Fed decision flaps its wings in Washington, who gets the storm?<br/>
  Now you can know.
</p>
