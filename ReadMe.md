<div align="center">

# ðŸ¦‹ butterfly-effect

### Type any world event. See the causal chain nobody else sees.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776ab.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com)
[![Stars](https://img.shields.io/github/stars/Om7035/butterfly-effect?style=social)](https://github.com/Om7035/butterfly-effect/stargazers)

![demo](demo.gif)

**[Try it in 60 seconds â†“](#try-it-now)**

</div>

---

## What is this?

butterfly-effect is an open-source causal chain engine. You type any event in plain English â€” a war, a rate hike, a hurricane, a product launch. It traces the cascade of effects across domains, out to the 3rd and 4th order, with timing and confidence scores.

It runs two parallel simulations (event vs. no-event), subtracts them, and shows you what actually changed and *when*. Not a chatbot. Not a prediction engine. A structural chain tracer â€” the one most analysts miss because they stop at the first-order effect.

---

## Try it now

```bash
git clone https://github.com/Om7035/butterfly-effect.git && cd butterfly-effect/backend
pip install fastapi uvicorn pydantic-settings loguru httpx google-genai mistralai networkx mesa
echo "GEMINI_API_KEY=your_key_here" >> .env
```

> Get a free Gemini key in 30 seconds: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

```bash
python -m uvicorn butterfly.main:app --port 8000
```

Open `http://localhost:8000/api/v1/demo/causal/demo_fed_jun2022` â€” you'll see a full causal chain instantly, no key needed.

For the full UI:

```bash
cd ../frontend && npm install && npm run dev
# â†’ http://localhost:3000
```

> No Docker. No database. Works on a clean machine in under 5 minutes.

---

## The "Holy Shit" Moment

**You type:** `Hamas attacks Israel â€” October 7, 2023`

**You get:**

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  CAUSAL CHAIN  Â·  12 diverging variables  Â·  confidence-weighted    â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                                                                     â”‚
â”‚  [1st order]  t + 2h                                                â”‚
â”‚  Hamas attack â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ IDF mobilization             â”‚
â”‚  confidence: 0.97                                                   â”‚
â”‚                                                                     â”‚
â”‚  [2nd order]  t + 6h                                                â”‚
â”‚  IDF mobilization â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ Brent crude +8.3%            â”‚
â”‚  confidence: 0.82  Â·  Strait of Hormuz risk premium                â”‚
â”‚  âš¡ Most analysts stop here.                                         â”‚
â”‚                                                                     â”‚
â”‚  [2nd order]  t + 72h                                               â”‚
â”‚  IDF mobilization â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ Red Sea shipping reroutes    â”‚
â”‚  confidence: 0.71  Â·  Houthi response forces Cape of Good Hope     â”‚
â”‚                                                                     â”‚
â”‚  [3rd order]  t + 96h                                               â”‚
â”‚  Red Sea disruption â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ Suez Canal traffic âˆ’40%      â”‚
â”‚  confidence: 0.85  Â·  Measurable within 4 days                     â”‚
â”‚                                                                     â”‚
â”‚  [3rd order]  t + 168h                                              â”‚
â”‚  Suez disruption â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ EU LNG spot prices +28%      â”‚
â”‚  confidence: 0.63  Â·  âš ï¸  Nobody is modeling this yet.             â”‚
â”‚                                                                     â”‚
â”‚  [4th order]  t + 720h  â† effect appears 30 days later             â”‚
â”‚  LNG price spike â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶ EU energy inflation restarts â”‚
â”‚  confidence: 0.58  Â·  âš ï¸  ECB declared victory in Sept 2023.       â”‚
â”‚                         This invalidates it.                        â”‚
â”‚                                                                     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

ðŸ’¡ What most people miss:
   The ECB's "mission accomplished" on inflation (Sept 2023) was
   invalidated by an event in Gaza â€” via a 6-hop chain with a 30-day lag.
   This showed up in Eurostat HICP data in Q1 2024.
   No Bloomberg terminal connected these dots in October 2023.
```

---

## Second Example â€” Different Domain

**You type:** `Fed raises rates 75bps â€” June 2022`

```
[1st order]  t + 2h    Fed decision â”€â”€â–¶ Treasury yield +75bps       (0.95)
[2nd order]  t + 48h   Treasury â”€â”€â”€â”€â”€â”€â–¶ Mortgage rate +92bps        (0.87)
[3rd order]  t + 168h  Mortgage â”€â”€â”€â”€â”€â”€â–¶ Housing starts âˆ’247k        (0.72)  âš ï¸
[4th order]  t + 720h  Housing â”€â”€â”€â”€â”€â”€â”€â–¶ Construction job losses      (0.54)  âš ï¸
             â†‘ effect appears 30 days after housing data

ðŸ’¡ The 4th-order effect shows up in JOLTS data 30 days after housing starts.
   Most economists attribute it to "the economy."
   The chain traces it to a specific FOMC meeting.
```

---

## How it works

```
  Your question
       â”‚
       â–¼
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ LLM PARSING â”‚  Gemini/Mistral identifies domains, actors, severity
  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜
         â”‚
         â–¼
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ EVIDENCE FETCH   â”‚  Wikipedia Â· FRED Â· DuckDuckGo Â· World Bank
  â”‚ (parallel, ~5s)  â”‚  GDELT Â· ReliefWeb Â· Open-Meteo Â· ACLED
  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚
         â–¼
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ CAUSAL DAG   â”‚  Domain template (Bernanke/IPCC/Ferguson) + graph edges
  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚
         â–¼
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ PARALLEL SIMULATION                      â”‚
  â”‚  Timeline A: event happens â†’ cascade     â”‚
  â”‚  Timeline B: no event â†’ baseline         â”‚
  â”‚  Diff: A(t) âˆ’ B(t) = true causal impact  â”‚
  â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
         â”‚
         â–¼
  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ CHAIN EXTRACTION â”‚  Hops ordered by timing Â· confidence scored
  â”‚ + LLM INSIGHTS   â”‚  Non-obvious effects surfaced
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

Simulation runs in **~0.01 seconds**. Total pipeline: **~40 seconds**.

---

## Add your own event

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "China invades Taiwan"}'
```

Streams Server-Sent Events. Watch the chain build in real time.

Or just type it in the UI at `http://localhost:3000`.

---

## Architecture

```
backend/butterfly/
â”œâ”€â”€ llm/           Multi-provider LLM  (Gemini â†’ Mistral â†’ Anthropic)
â”œâ”€â”€ ingestion/     8 evidence sources  (Wikipedia, FRED, DuckDuckGo, ...)
â”œâ”€â”€ causal/        DAG builder Â· synthetic control Â· chain extractor
â”œâ”€â”€ simulation/    Mesa ABM Â· domain agents Â· parallel runner
â”œâ”€â”€ pipeline/      Orchestrator Â· SSE streaming Â· graceful degradation
â””â”€â”€ db/            Neo4j Â· Postgres Â· Redis  (all optional)

frontend/
â”œâ”€â”€ app/           Next.js 14  (/ Â· /demo Â· /graph-demo)
â””â”€â”€ components/    React Flow graph Â· insight cards Â· temporal replay
```

**Algorithms used:**

| Layer | Algorithm | Reference |
|-------|-----------|-----------|
| Causal identification | DoWhy backdoor + OLS / Poisson GLM / Logistic / Ordered logit | Pearl (2009), Angrist & Pischke (2009) |
| Counterfactual | Synthetic control â€” SLSQP weight optimization + placebo tests | Abadie & Gardeazabal (2003) |
| Simulation | Mesa ABM â€” linear / exponential / sigmoid / step reaction functions | â€” |
| Chain extraction | Divergence threshold (2%) Â· confidence = 0.4Ã—log + 0.4Ã—magnitude + 0.2Ã—persistence | â€” |
| Cycle detection | DFS â€” weakest edge removal | â€” |
| Outcome typing | Auto-detect: binary / count / rate / ordinal / continuous | Agresti (2013) |

**DAG templates** (domain-specific starting points):

- `FINANCIAL_TEMPLATE` â€” Bernanke (2005) monetary transmission
- `GEOPOLITICAL_TEMPLATE` â€” Collier & Hoeffler (2004) conflict economics
- `CLIMATE_TEMPLATE` â€” IPCC AR6 (2021) impact pathways
- `PANDEMIC_TEMPLATE` â€” Ferguson et al. (2020)
- `TECH_DISRUPTION_TEMPLATE` â€” Brynjolfsson & McAfee (2014)

**Stack:** FastAPI Â· Python 3.10+ Â· Mesa Â· Next.js 14 Â· React Flow Â· Framer Motion Â· Gemini Â· Mistral Â· FRED Â· Wikipedia Â· DuckDuckGo Â· World Bank Â· GDELT

---

## Contributing

The fastest contribution: add a new domain.

**Step 1** â€” Add agent templates in `backend/butterfly/simulation/dynamic_agents.py`:

```python
AGENT_TEMPLATES["cryptocurrency"] = [
    _make_profile(
        "Crypto Exchange", "market", "cryptocurrency",
        "maximize trading volume",
        triggers=[{"variable": "btc_price_delta", "operator": ">", "threshold": 0.1,
                   "condition": "btc_price_delta > 0.1"}],
        reactions=[{"target_variable": "trading_volume", "formula": "exponential",
                    "magnitude": 2.0, "direction": 1, "lag_steps": 1}],
    ),
]
```

**Step 2** â€” Add keywords in `backend/butterfly/llm/event_parser.py` â†’ `_DOMAIN_KEYWORDS`

**Step 3** â€” Add fetchers in `backend/butterfly/ingestion/universal_fetcher.py` â†’ `DOMAIN_FETCHER_MAP`

**Step 4** â€” Add a test in `backend/tests/test_universal/` (see existing tests for pattern)

**Step 5** â€” Open a PR with: domain name Â· one worked example Â· test passing

Other ways to help:
- Found a wrong causal chain? Open an issue with the question + what was wrong
- New free data source? Add a fetcher to `universal_fetcher.py`
- Frontend improvements? The graph visualization has a lot of room to grow

```bash
git checkout -b feat/domain-cryptocurrency
pytest backend/tests/test_universal/ -v
git push origin feat/domain-cryptocurrency
```

---

## License

MIT â€” do whatever you want with it.

Built by [Om Kawale](https://github.com/Om7035).
If this is useful, a â­ helps more people find it.

---

<div align="center">
<sub>butterfly-effect Â· making the invisible visible Â· MIT license</sub>
</div>
