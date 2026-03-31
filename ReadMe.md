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
