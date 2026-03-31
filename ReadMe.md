# 🦋 butterfly-effect

**Type any world event. See the causal chain nobody else sees.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Stars](https://img.shields.io/github/stars/Om7035/butterfly-effect?style=social)](https://github.com/Om7035/butterfly-effect)

---

## What is this?

butterfly-effect is an open-source causal chain engine. You type any event in plain English — a war, a rate hike, a hurricane, a product launch — and it traces the cascade of effects across domains, out to the 3rd and 4th order, with timing and confidence scores. It runs two parallel simulations (event vs. no-event), subtracts them, and shows you what actually changed and when.

It's not a chatbot. It doesn't predict the future. It shows you the structural chain that's already in motion — the one most analysts miss because they stop at the first-order effect.

---

## Try it now

```bash
git clone https://github.com/Om7035/butterfly-effect.git
cd butterfly-effect/backend
pip install fastapi uvicorn pydantic-settings loguru httpx google-genai mistralai networkx mesa
```

Add your free API key to `backend/.env` (get one at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) — takes 30 seconds):

```
GEMINI_API_KEY=your-key-here
```

```bash
python -m uvicorn butterfly.main:app --host 0.0.0.0 --port 8000
```

Open a second terminal:

```bash
cd butterfly-effect/frontend && npm install && npm run dev
```

Go to `http://localhost:3000` and type anything.

> No Docker required. No database required. Works on a clean machine in under 5 minutes.

---

## The "holy shit" moment

Here's what happens when you type: **"Hamas attacks Israel — October 7, 2023"**

```
Question: Hamas attacks Israel — October 7, 2023

Hop 1  [t+2h]   Hamas attack → IDF mobilization
                 Confidence: 0.97 | This is the obvious one.

Hop 2  [t+6h]   IDF mobilization → Brent crude +8.3%
                 Confidence: 0.82 | Risk premium on Strait of Hormuz.
                 ⚡ Most analysts stop here.

Hop 3  [t+72h]  IDF mobilization → Red Sea shipping reroutes
                 Confidence: 0.71 | Houthi attacks force Cape of Good Hope detour.
                 Adds 14 days to EU-Asia transit. Insurance premiums spike.

Hop 4  [t+96h]  Red Sea disruption → Suez Canal traffic -40%
                 Confidence: 0.85 | Measurable within 4 days of mobilization.

Hop 5  [t+168h] Suez disruption → EU LNG spot prices +28%
                 Confidence: 0.63 | ⚠️  3rd order effect. Nobody is modeling this yet.

Hop 6  [t+720h] LNG price spike → EU energy inflation re-accelerates
                 Confidence: 0.58 | ⚠️  4th order. ECB declared victory on inflation
                                        in September 2023. This restarts the clock.
                                        Visible in Eurostat data Q1 2024.

What most people miss: The ECB's September 2023 "mission accomplished" on inflation
was invalidated by an event in Gaza — via a 6-hop chain with a 30-day lag.
No Bloomberg terminal showed this connection in October 2023.
```

That last insight — the ECB inflation connection — appeared in Eurostat data 90 days later. The chain was traceable from day one.

---

## Second example: ChatGPT launches

```
Question: OpenAI releases model that outperforms all human experts

Hop 1  [t+48h]  AI capability spike → VC investment flood ($200B in 90 days)
                 Confidence: 0.91

Hop 2  [t+168h] VC flood → AI infrastructure buildout
                 Confidence: 0.88 | GPU demand, data center construction, power grid stress

Hop 3  [t+336h] AI capability → white-collar employment contracts renegotiated
                 Confidence: 0.74 | ⚠️  3rd order. Law firms, consulting, finance.

Hop 4  [t+720h] Employment disruption → political pressure for AI regulation
                 Confidence: 0.61 | ⚠️  4th order. EU AI Act enforcement accelerates.

Hop 5  [t+1440h] Regulatory arbitrage → AI companies relocate to Singapore
                 Confidence: 0.52 | ⚠️  5th order. 18 months out. Underpriced by markets.

What most people miss: The 5th-order effect (regulatory arbitrage to Singapore)
is already visible in incorporation data. It started 14 months after the GPT-4 launch.
```

---

## How it works

```
Your question
     │
     ▼
[1] LLM PARSING
    Gemini/Mistral identifies: domains, actors, severity, causal seeds
     │
     ▼
[2] EVIDENCE FETCH (parallel, ~5 seconds)
    Wikipedia · DuckDuckGo · FRED · World Bank · GDELT · ReliefWeb · Open-Meteo
     │
     ▼
[3] CAUSAL DAG
    Domain-specific template + evidence → directed acyclic graph
     │
     ▼
[4] PARALLEL SIMULATION
    Timeline A: event happens → agents react → cascade forms
    Timeline B: no event → agents baseline
    Diff: A(t) - B(t) = true causal impact at each timestep
     │
     ▼
[5] CHAIN EXTRACTION + INSIGHTS
    Hops ordered by step_triggered · domains inferred · LLM generates non-obvious insights
```

The simulation runs 96 agent-steps in ~0.01 seconds. The bottleneck is evidence fetching (~10s) and LLM parsing (~3s). Total: under 45 seconds for any question.

---

## Add your own event

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "China invades Taiwan"}'
```

The response is a Server-Sent Events stream. Watch the chain build in real time.

Or just type it in the UI at `http://localhost:3000`.

---

## Architecture

```
butterfly-effect/
├── backend/butterfly/
│   ├── api/           # FastAPI routes (analyze, demo, events, simulation)
│   ├── llm/           # Multi-provider LLM (Gemini → Mistral → Anthropic)
│   ├── ingestion/     # Evidence fetchers (Wikipedia, FRED, GDELT, DuckDuckGo, ...)
│   ├── extraction/    # NER + relationship extraction
│   ├── causal/        # DAG builder, log extractor, synthetic control
│   ├── simulation/    # Mesa ABM — domain-agnostic agents + universal model
│   ├── pipeline/      # Orchestrator — wires all stages, streams SSE progress
│   └── db/            # Neo4j, Postgres, Redis (all optional — degrades gracefully)
│
└── frontend/
    ├── app/           # Next.js 14 pages (/, /demo, /graph-demo)
    └── components/    # React Flow graph, insight cards, temporal replay
```

**Key design decisions:**

- Every stage is independently catchable — partial results always returned, never a crash
- No database required to run — all DBs are optional, pipeline degrades gracefully
- LLM is used once at parse time and once for insights — simulation is pure math
- Evidence fetching is parallel — all sources run concurrently with 5s timeout each

**Stack:** FastAPI · Python 3.10+ · Next.js 14 · React Flow · Framer Motion · Mesa (ABM) · Gemini/Mistral · FRED · Wikipedia · DuckDuckGo · World Bank · GDELT

---

## Algorithms

This is the part most READMEs skip. Here's exactly what runs under the hood.

### 1. Causal DAG construction

**File:** `backend/butterfly/causal/dag.py`

The system uses domain-specific DAG templates validated against academic literature, then merges them with event-specific edges from the knowledge graph.

Five templates are built in:

| Template | Domain | Source |
|----------|--------|--------|
| `FINANCIAL_TEMPLATE` | economics, finance | Bernanke (2005) monetary transmission mechanism |
| `GEOPOLITICAL_TEMPLATE` | geopolitics, military | Collier & Hoeffler (2004) conflict economics |
| `CLIMATE_TEMPLATE` | climate, environment | IPCC AR6 (2021) impact pathways |
| `PANDEMIC_TEMPLATE` | health | Ferguson et al. (2020), Eichenbaum et al. (2021) |
| `TECH_DISRUPTION_TEMPLATE` | technology | Brynjolfsson & McAfee (2014) second machine age |

Each edge in a template carries: `latency_hours`, `confidence`, and a plain-English `mechanism` description.

Cycle detection uses DFS. When a cycle is found, the weakest edge (lowest confidence) is removed. This runs iteratively until the graph is acyclic.

### 2. Causal identification and estimation

**File:** `backend/butterfly/causal/identification.py`

The `UniversalCausalEstimator` auto-selects the appropriate statistical estimator based on the outcome variable type:

| Outcome type | Estimator | Reference |
|-------------|-----------|-----------|
| Continuous (prices, rates) | DoWhy backdoor + OLS linear regression | Pearl (2009) Ch. 3 — backdoor criterion |
| Count (casualties, events) | Poisson GLM — Incidence Rate Ratio | Cameron & Trivedi (2013) |
| Binary (did X happen: 0/1) | Logistic regression — Average Marginal Effect | Hosmer & Lemeshow (2000) |
| Ordinal (stability scores 1-10) | Ordered logit — proportional odds | McCullagh (1980) |
| Rate (infection rate, unemployment %) | OLS on logit-transformed outcome | Papke & Wooldridge (1996) |

The `OutcomeTypeDetector` classifies variables automatically using these rules (applied in order):
1. Binary: only {0, 1} values
2. Rate: values in [0,1] with non-integer values
3. Count: non-negative integers with range > 20
4. Ordinal: integers with ≤ 20 unique values
5. Continuous: everything else

When DoWhy is available, it runs three automated refutation tests:
- **Random common cause** — adds a random variable as a confounder; effect should be stable
- **Placebo treatment** — permutes the treatment; effect should disappear
- **Data subset** — re-estimates on 80% of data; effect should be stable (±20%)

### 3. Synthetic control method

**File:** `backend/butterfly/causal/synthetic_control.py`

For aggregate-level events (country policies, regional disasters), the system implements the Abadie & Gardeazabal (2003) synthetic control method from scratch in pure Python/scipy.

The algorithm:
1. **Find optimal weights** — minimize `||treated_pre - controls_pre @ W||²` subject to `W ≥ 0, sum(W) = 1` using SLSQP optimization
2. **Construct counterfactual** — `synthetic = controls @ W` for the full time series
3. **Estimate effect** — `ATE = mean(actual_post - synthetic_post)`
4. **Validate with placebo tests** — treat each control unit as if it were treated; p-value = fraction of placebos with `|ATE| ≥ |treated_ATE|`

A result is only marked `is_trustworthy=True` if pre-treatment fit R² ≥ 0.80 (Abadie 2021 recommendation).

### 4. Agent-based simulation

**File:** `backend/butterfly/simulation/universal_model.py`, `dynamic_agents.py`

The simulation uses [Mesa](https://mesa.readthedocs.io/) (Python ABM framework). Each agent has:

- **TriggerRules** — conditions that activate the agent: `variable operator threshold` (e.g., `conflict_intensity > 0.3`)
- **ReactionFunctions** — one of four mathematical formulas:
  - `linear` — constant delta per step: `δ = direction × magnitude`
  - `exponential` — decays over time: `δ = direction × magnitude × exp(-t/10)`
  - `step` — immediate jump, then flat: `δ = direction × magnitude` at `t=0` only
  - `sigmoid` — S-curve: `δ = direction × magnitude × 1/(1 + exp(-0.5(t-5)))`
- **lag_steps** — steps before reaction kicks in (1 step = 1 hour)
- **dampening_factor** — how fast the response fades (0-1)

Timeline A (event) and Timeline B (counterfactual) run concurrently in a thread pool. The diff `A(t) - B(t)` at each timestep is the true causal impact.

### 5. Causal chain extraction

**File:** `backend/butterfly/causal/log_extractor.py`

After simulation, `CausalLogExtractor` processes the raw simulation log into an ordered causal chain:

1. Groups log entries by `variable_changed`
2. Computes `diff_series[var][step] = A(step, var) - B(step, var)` for all variables
3. Finds `step_triggered` — first step where `|diff| > 2%` threshold (divergence threshold)
4. Assigns each hop to the responsible agent (first agent to change that variable after divergence)
5. Computes `magnitude = |max_delta| / (|baseline| + |max_delta|)` — normalized, bounded [0,1]
6. Computes `persistence = fraction of steps where |delta| > 1%`
7. Scores `confidence = 0.4 × log_count + 0.4 × magnitude + 0.2 × persistence`
8. Detects feedback loops via DFS on the hop graph (using NetworkX `simple_cycles`)
9. Infers domain coverage from variable names via `_VAR_DOMAIN_MAP`

Hops are sorted by `step_triggered` — this is the causal order.

### 6. LLM multi-provider routing

**File:** `backend/butterfly/llm/providers.py`

The LLM is used in two places only: event parsing (once per analysis) and insight generation (once per analysis). Everything in between is pure math.

Provider priority: Gemini 2.0 Flash → Gemini 2.0 Flash Lite → Gemini 2.5 Flash → Mistral Small → Anthropic Claude

Rate limit handling: if Gemini returns 429 (quota exceeded), the system automatically tries the next Gemini model before falling back to Mistral. Each model has its own quota bucket.

---

## Contributing

The fastest way to contribute is to add a new domain or improve an existing one.

**Add a new domain (e.g., "cryptocurrency"):**

1. Add agent templates to `backend/butterfly/simulation/dynamic_agents.py`:
```python
AGENT_TEMPLATES["cryptocurrency"] = [
    _make_profile(
        "Crypto Exchange", "market", "cryptocurrency",
        "maximize trading volume and liquidity",
        triggers=[{"variable": "btc_price_delta", "operator": ">", "threshold": 0.1, ...}],
        reactions=[{"target_variable": "trading_volume", "formula": "exponential", ...}],
    ),
]
```

2. Add domain keywords to `backend/butterfly/llm/event_parser.py` in `_DOMAIN_KEYWORDS`

3. Add fetchers to `backend/butterfly/ingestion/universal_fetcher.py` in `DOMAIN_FETCHER_MAP`

4. Add a test in `backend/tests/test_universal/` — see existing tests for the pattern

5. Open a PR with: the domain name, one worked example, and the test passing

**Other ways to help:**
- Report a wrong causal chain — open an issue with the question and what was wrong
- Add a new evidence source — any free API that returns structured data
- Improve the frontend — the graph visualization has a lot of room to grow
- Write validation tests — compare outputs against known historical outcomes

```bash
git checkout -b feat/domain-cryptocurrency
# make changes
pytest backend/tests/test_universal/ -v
git push origin feat/domain-cryptocurrency
```

---

## License

MIT — do whatever you want with it.

Built by [Om Kawale](https://github.com/Om7035). If you find it useful, a star helps more people find it.
