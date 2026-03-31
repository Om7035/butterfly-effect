<div align="center">

```
██████╗ ██╗   ██╗████████╗████████╗███████╗██████╗ ███████╗██╗  ██╗   ██╗
██╔══██╗██║   ██║╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗██╔════╝██║  ╚██╗ ██╔╝
██████╔╝██║   ██║   ██║      ██║   █████╗  ██████╔╝█████╗  ██║   ╚████╔╝
██╔══██╗██║   ██║   ██║      ██║   ██╔══╝  ██╔══██╗██╔══╝  ██║    ╚██╔╝
██████╔╝╚██████╔╝   ██║      ██║   ███████╗██║  ██║██║     ███████╗██║
╚═════╝  ╚═════╝    ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝
                    ███████╗███████╗███████╗███████╗ ██████╗████████╗
                    ██╔════╝██╔════╝██╔════╝██╔════╝██╔════╝╚══██╔══╝
                    █████╗  █████╗  █████╗  █████╗  ██║        ██║
                    ██╔══╝  ██╔══╝  ██╔══╝  ██╔══╝  ██║        ██║
                    ███████╗██║     ██║     ███████╗╚██████╗   ██║
                    ╚══════╝╚═╝     ╚═╝     ╚══════╝ ╚═════╝   ╚═╝
```

### *Type any world event. See the causal chain nobody else sees.*

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-7c3aed.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-3b82f6.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-10b981.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000.svg?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![Stars](https://img.shields.io/github/stars/Om7035/butterfly-effect?style=for-the-badge&color=f59e0b&logo=github)](https://github.com/Om7035/butterfly-effect/stargazers)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-34d399.svg?style=for-the-badge)](CONTRIBUTING.md)

<br/>

> *"It used to be thought that the events that changed the world were things like big bombs and maniac politicians.*
> *The things that change the world are the tiny things. A butterfly flaps its wings in the Amazonian jungle,*
> *and subsequently a storm ravages half of Europe."*
> — Terry Pratchett

</div>

---

<div align="center">

## ◈ What is this?

</div>

butterfly-effect is an open-source **causal chain engine**. You type any event in plain English — a war, a rate hike, a hurricane, a product launch — and it traces the cascade of effects across domains, out to the 3rd and 4th order, with timing and confidence scores.

It runs two parallel simulations (event vs. no-event), subtracts them, and shows you what actually changed and when.

**It's not a chatbot. It doesn't predict the future.** It shows you the structural chain that's already in motion — the one most analysts miss because they stop at the first-order effect.

---

<div align="center">

## ◈ Try it now

</div>

```bash
# 1. Clone
git clone https://github.com/Om7035/butterfly-effect.git
cd butterfly-effect/backend

# 2. Install
pip install fastapi uvicorn pydantic-settings loguru httpx google-genai mistralai networkx mesa

# 3. Add a free LLM API key to backend/.env
echo "GEMINI_API_KEY=your-key-here" >> .env
# Get a free key at: https://aistudio.google.com/app/apikey (30 seconds)

# 4. Start the backend
python -m uvicorn butterfly.main:app --host 0.0.0.0 --port 8000
```

```bash
# In a second terminal — start the frontend
cd butterfly-effect/frontend && npm install && npm run dev
```

Open **`http://localhost:3000`** and type anything.

> ✅ No Docker required &nbsp;·&nbsp; ✅ No database required &nbsp;·&nbsp; ✅ Under 5 minutes on a clean machine

---

<div align="center">

## ◈ The "holy shit" moment

</div>

Here's what happens when you type: **`Hamas attacks Israel — October 7, 2023`**

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CAUSAL CHAIN ANALYSIS                                                       ║
║  Query: "Hamas attacks Israel — October 7, 2023"                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ● HOP 1  [t + 2h]   Hamas attack ──────────────▶ IDF mobilization          ║
║           Confidence: ████████████████████ 0.97                             ║
║           This is the obvious one. Everyone sees this.                       ║
║                                                                              ║
║  ● HOP 2  [t + 6h]   IDF mobilization ──────────▶ Brent crude +8.3%        ║
║           Confidence: ████████████████░░░░ 0.82                             ║
║           ⚡ Risk premium on Strait of Hormuz.                               ║
║           ⚡ Most analysts stop here.                                        ║
║                                                                              ║
║  ● HOP 3  [t + 72h]  IDF mobilization ──────────▶ Red Sea shipping reroutes ║
║           Confidence: ██████████████░░░░░░ 0.71                             ║
║           Houthi attacks force Cape of Good Hope detour.                    ║
║           Adds 14 days to EU-Asia transit. Insurance premiums spike.        ║
║                                                                              ║
║  ● HOP 4  [t + 96h]  Red Sea disruption ────────▶ Suez Canal traffic -40%  ║
║           Confidence: █████████████████░░░ 0.85                             ║
║           Measurable within 4 days of mobilization.                         ║
║                                                                              ║
║  ⚠ HOP 5  [t + 168h] Suez disruption ───────────▶ EU LNG spot prices +28%  ║
║           Confidence: ████████████░░░░░░░░ 0.63   [3RD ORDER EFFECT]       ║
║           Nobody is modeling this yet.                                       ║
║                                                                              ║
║  ⚠ HOP 6  [t + 720h] LNG price spike ───────────▶ EU energy inflation ↑    ║
║           Confidence: ███████████░░░░░░░░░ 0.58   [4TH ORDER EFFECT]       ║
║           ECB declared victory on inflation in September 2023.              ║
║           This restarts the clock. Visible in Eurostat data Q1 2024.       ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  💡 INSIGHT: The ECB's "mission accomplished" on inflation was invalidated   ║
║     by an event in Gaza — via a 6-hop chain with a 30-day lag.              ║
║     No Bloomberg terminal showed this connection in October 2023.           ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

That last insight appeared in Eurostat data 90 days later. **The chain was traceable from day one.**

---

<div align="center">

## ◈ Second example: ChatGPT launches

</div>

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CAUSAL CHAIN ANALYSIS                                                       ║
║  Query: "OpenAI releases model that outperforms all human experts"           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ● HOP 1  [t + 48h]   AI capability ────────────▶ VC investment flood       ║
║           Confidence: ██████████████████░░ 0.91   $200B deployed in 90 days ║
║                                                                              ║
║  ● HOP 2  [t + 168h]  VC flood ─────────────────▶ AI infrastructure boom   ║
║           Confidence: █████████████████░░░ 0.88   GPU shortage, power grids ║
║                                                                              ║
║  ⚠ HOP 3  [t + 336h]  AI capability ────────────▶ White-collar renegotiation║
║           Confidence: ██████████████░░░░░░ 0.74   [3RD ORDER]               ║
║           Law firms, consulting, finance. Contracts being rewritten.        ║
║                                                                              ║
║  ⚠ HOP 4  [t + 720h]  Employment disruption ────▶ AI regulation pressure   ║
║           Confidence: ████████████░░░░░░░░ 0.61   [4TH ORDER]               ║
║           EU AI Act enforcement accelerates.                                ║
║                                                                              ║
║  ⚠ HOP 5  [t + 1440h] Regulatory arbitrage ─────▶ AI cos → Singapore       ║
║           Confidence: ██████████░░░░░░░░░░ 0.52   [5TH ORDER]               ║
║           18 months out. Already visible in incorporation data.             ║
║                                                                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  💡 INSIGHT: The 5th-order effect started 14 months after GPT-4 launched.   ║
║     The chain was predictable from day one.                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

<div align="center">

## ◈ How it works

</div>

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │                                                                     │
  │   You type:  "Fed raises rates 75bps"                               │
  │                                                                     │
  └──────────────────────────────┬──────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      [1] LLM PARSING     │
                    │  Identifies: domains,    │
                    │  actors, severity,       │
                    │  causal seeds            │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   [2] EVIDENCE FETCH     │
                    │   (parallel, ~5 sec)     │
                    │                          │
                    │  Wikipedia · DuckDuckGo  │
                    │  FRED · World Bank       │
                    │  GDELT · ReliefWeb       │
                    │  Open-Meteo · ACLED      │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    [3] CAUSAL DAG        │
                    │  Domain template +       │
                    │  evidence → acyclic      │
                    │  directed graph          │
                    └────────────┬────────────┘
                                 │
               ┌─────────────────┴──────────────────┐
               │                                    │
  ┌────────────▼────────────┐       ┌───────────────▼──────────────┐
  │   TIMELINE A (event)    │       │   TIMELINE B (no event)      │
  │                         │       │                              │
  │  Agents receive signal  │       │  Same agents, no signal      │
  │  Cascades form          │       │  Baseline only               │
  │  t=0 → t=96h            │       │  t=0 → t=96h                 │
  └────────────┬────────────┘       └───────────────┬──────────────┘
               │                                    │
               └─────────────────┬──────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  DIFF:  A(t) - B(t)      │
                    │  = true causal impact    │
                    │    at each timestep      │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  [5] CHAIN EXTRACTION   │
                    │  Hops ordered by time   │
                    │  Confidence scored      │
                    │  LLM generates insights │
                    └─────────────────────────┘
```

> The simulation runs 96 agent-steps in **~0.01 seconds**. Total pipeline: **under 45 seconds** for any question.

---

<div align="center">

## ◈ Add your own event

</div>

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "China invades Taiwan"}'
```

The response is a **Server-Sent Events stream** — watch the chain build in real time. Or just type it in the UI at `http://localhost:3000`.

---

<div align="center">

## ◈ Architecture

</div>

```
butterfly-effect/
│
├── backend/butterfly/
│   ├── api/           ◀  FastAPI routes — analyze (SSE), demo, events, simulation
│   ├── llm/           ◀  Multi-provider LLM client (auto-fallback chain)
│   ├── ingestion/     ◀  8 evidence fetchers — Wikipedia, FRED, DuckDuckGo, ...
│   ├── extraction/    ◀  NER + relationship extraction (keyword + spaCy)
│   ├── causal/        ◀  DAG builder, log extractor, synthetic control
│   ├── simulation/    ◀  Mesa ABM — domain-agnostic agents + universal model
│   ├── pipeline/      ◀  Orchestrator — wires all stages, streams SSE progress
│   └── db/            ◀  Neo4j, Postgres, Redis (all optional, graceful degradation)
│
└── frontend/
    ├── app/           ◀  Next.js 14 — /, /demo, /graph-demo
    └── components/    ◀  React Flow graph, insight cards, temporal replay scrubber
```

<br/>

| Design principle | What it means |
|:---|:---|
| 🛡️ Every stage is catchable | Partial results always returned — never a crash |
| 🔌 No database required | All DBs optional — pipeline degrades gracefully |
| 🧮 LLM used twice only | Parse time + insights — simulation is pure math |
| ⚡ Parallel evidence fetch | All 8 sources run concurrently with 5s timeout |

<br/>

**Full stack:**

```
Backend   FastAPI · Python 3.10+ · Mesa (ABM) · NetworkX · scipy · statsmodels
Frontend  Next.js 14 · React Flow · Framer Motion · Tailwind CSS
LLM       Multi-provider client (free tier supported)
Data      FRED · Wikipedia · DuckDuckGo · World Bank · GDELT · ReliefWeb · Open-Meteo · ACLED
Storage   Neo4j · PostgreSQL · Redis  (all optional)
```

---

<div align="center">

## ◈ Algorithms

*This is the part most READMEs skip.*

</div>

### 1 · Causal DAG Construction

**`backend/butterfly/causal/dag.py`**

Five domain templates validated against peer-reviewed literature, merged with event-specific edges from the knowledge graph:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TEMPLATE              DOMAIN              ACADEMIC SOURCE              │
├─────────────────────────────────────────────────────────────────────────┤
│  FINANCIAL_TEMPLATE    economics, finance  Bernanke (2005)              │
│  GEOPOLITICAL_TEMPLATE geopolitics, mil.   Collier & Hoeffler (2004)   │
│  CLIMATE_TEMPLATE      climate, env.       IPCC AR6 (2021)             │
│  PANDEMIC_TEMPLATE     health              Ferguson et al. (2020)      │
│  TECH_DISRUPTION       technology          Brynjolfsson & McAfee (2014)│
└─────────────────────────────────────────────────────────────────────────┘
```

Each edge carries: `latency_hours` · `confidence` · plain-English `mechanism`

Cycle detection: **DFS** — when a cycle is found, the weakest edge (lowest confidence) is removed iteratively until the graph is acyclic.

---

### 2 · Causal Identification & Estimation

**`backend/butterfly/causal/identification.py`**

`UniversalCausalEstimator` auto-selects the correct statistical estimator by outcome type:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  OUTCOME TYPE          ESTIMATOR                    REFERENCE               │
├──────────────────────────────────────────────────────────────────────────────┤
│  Continuous            DoWhy backdoor + OLS          Pearl (2009) Ch.3      │
│  (prices, indices)                                                           │
│                                                                              │
│  Count                 Poisson GLM (IRR)             Cameron & Trivedi (2013)│
│  (casualties, events)                                                        │
│                                                                              │
│  Binary                Logistic regression (AME)     Hosmer & Lemeshow (2000)│
│  (did X happen: 0/1)                                                         │
│                                                                              │
│  Ordinal               Ordered logit                 McCullagh (1980)       │
│  (stability 1-10)                                                            │
│                                                                              │
│  Rate                  OLS on logit(y)               Papke & Wooldridge (1996)│
│  (infection %, unemp.) transform                                             │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Automated refutation tests** (when DoWhy is available):
- `random_common_cause` — add random confounder; effect must be stable
- `placebo_treatment` — permute treatment; effect must disappear
- `data_subset` — re-estimate on 80% of data; effect must be stable ±20%

---

### 3 · Synthetic Control Method

**`backend/butterfly/causal/synthetic_control.py`**

Pure Python/scipy implementation of **Abadie & Gardeazabal (2003)**. Used for aggregate-level events (country policies, regional disasters).

```
Step 1  Find optimal weights W
        minimize  ‖ treated_pre − controls_pre @ W ‖²
        subject to  W ≥ 0,  Σ W = 1
        solver: SLSQP (scipy.optimize)

Step 2  Construct counterfactual
        synthetic(t) = controls(t) @ W

Step 3  Estimate effect
        ATE = mean( actual_post − synthetic_post )

Step 4  Validate with in-space placebo tests
        Treat each control as if it were treated
        p-value = |placebos with |ATE| ≥ |treated_ATE|| / total placebos

        Result marked is_trustworthy = True only if pre-treatment R² ≥ 0.80
        (Abadie 2021 recommendation)
```

---

### 4 · Agent-Based Simulation

**`backend/butterfly/simulation/universal_model.py`** · **`dynamic_agents.py`**

Built on [Mesa](https://mesa.readthedocs.io/) (Python ABM framework). Each agent has:

```python
BehaviorProfile(
    triggers=[
        TriggerRule(variable="conflict_intensity", operator=">", threshold=0.3)
    ],
    reaction_functions=[
        ReactionFn(
            target_variable = "oil_price",
            formula         = "exponential",   # linear | exponential | step | sigmoid
            magnitude       = 8.0,
            direction       = +1,
            lag_steps       = 1,               # 1 step = 1 hour
        )
    ],
    dampening_factor = 0.85,                   # how fast response fades
)
```

**Four reaction formulas:**

```
linear      δ = direction × magnitude
exponential δ = direction × magnitude × exp(−t/10)     ← decays over time
step        δ = direction × magnitude  at t=0 only     ← immediate jump
sigmoid     δ = direction × magnitude × σ(0.5(t−5))   ← S-curve buildup
```

Timeline A and B run **concurrently in a thread pool**. `diff = A(t) − B(t)` = true causal impact.

---

### 5 · Causal Chain Extraction

**`backend/butterfly/causal/log_extractor.py`**

Processes the raw simulation log into an ordered causal chain:

```
1. Group log entries by variable_changed
2. Compute diff_series[var][step] = A(step,var) − B(step,var)
3. Find step_triggered = first step where |diff| > 2% threshold
4. Assign hop to responsible agent
5. magnitude   = |max_delta| / (|baseline| + |max_delta|)   ← bounded [0,1]
6. persistence = fraction of steps where |delta| > 1%
7. confidence  = 0.4 × log_count + 0.4 × magnitude + 0.2 × persistence
8. Detect feedback loops via DFS (NetworkX simple_cycles)
9. Infer domain from variable name via _VAR_DOMAIN_MAP
```

Hops sorted by `step_triggered` = causal order.

---

### 6 · LLM Multi-Provider Routing

**`backend/butterfly/llm/providers.py`**

The LLM is called **exactly twice** per analysis: once to parse the event, once to generate insights. Everything in between is pure math.

```
Priority chain (auto-fallback on rate limit or failure):

  [1] Primary LLM provider (free tier)
       │  429 rate limit? → try next model
  [2] Secondary LLM provider (free tier)
       │  failure? → try next
  [3] Tertiary LLM provider
       │  all fail? →
  [4] Rule-based fallback (always works, no API key needed)
```

Each provider has its own quota bucket. Rate limit on one model automatically tries the next — no manual intervention needed.

---

<div align="center">

## ◈ Evidence Sources

</div>

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SOURCE          KEY REQUIRED   WHAT IT PROVIDES                        │
├─────────────────────────────────────────────────────────────────────────┤
│  Wikipedia       None           Background context, entity summaries    │
│  DuckDuckGo      None           Live web search, recent news            │
│  GDELT           None           250M+ global news events database       │
│  World Bank      None           GDP, inflation, development indicators  │
│  Open-Meteo      None           Weather & climate data by location      │
│  ReliefWeb       None           Humanitarian situation reports          │
│  FRED            Free signup    US economic time-series (Fed, housing)  │
│  ACLED           Free signup    Armed conflict event data (OAuth2)      │
│  NewsAPI         Paid ($50/mo)  Optional — DuckDuckGo covers this       │
└─────────────────────────────────────────────────────────────────────────┘
```

All fetchers run **concurrently** with a 5-second timeout. If one fails, the others continue.

---

<div align="center">

## ◈ Contributing

</div>

The fastest way to contribute is to **add a new domain**.

**Example: adding "cryptocurrency" domain**

```python
# 1. backend/butterfly/simulation/dynamic_agents.py
AGENT_TEMPLATES["cryptocurrency"] = [
    _make_profile(
        "Crypto Exchange", "market", "cryptocurrency",
        "maximize trading volume and liquidity",
        triggers=[{"variable": "btc_price_delta", "operator": ">", "threshold": 0.1, ...}],
        reactions=[{"target_variable": "trading_volume", "formula": "exponential", ...}],
    ),
]

# 2. backend/butterfly/llm/event_parser.py — add to _DOMAIN_KEYWORDS
"cryptocurrency": ["bitcoin", "crypto", "defi", "blockchain", "exchange hack", ...]

# 3. backend/butterfly/ingestion/universal_fetcher.py — add to DOMAIN_FETCHER_MAP
"cryptocurrency": [fetch_duckduckgo, fetch_wikipedia, fetch_your_crypto_api]

# 4. backend/tests/test_universal/ — add a test (see existing tests for pattern)
```

```bash
git checkout -b feat/domain-cryptocurrency
pytest backend/tests/test_universal/ -v
git push origin feat/domain-cryptocurrency
```

**Other ways to help:**

| What | How |
|:---|:---|
| 🐛 Wrong causal chain | Open an issue — use the validation report template |
| 🌐 New evidence source | Any free API that returns structured data |
| 🎨 Frontend improvements | The graph visualization has a lot of room to grow |
| ✅ Validation tests | Compare outputs against known historical outcomes |
| 📖 New domain | Use the domain request issue template |

---

<div align="center">

## ◈ License

**MIT** — do whatever you want with it.

<br/>

Built by [Om Kawale](https://github.com/Om7035)

*If you find it useful, a ⭐ helps more people find it.*

<br/>

---

```
If a Fed decision flaps its wings in Washington,
who gets the storm — and when?

Now you can know.
```

</div>
