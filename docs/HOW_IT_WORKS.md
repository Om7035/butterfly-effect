# How butterfly-effect works

For people who want to understand the internals before contributing or building on top of it.

---

## The 4 ingredients

Every analysis runs through 4 stages. Each stage can fail independently — the pipeline always returns a partial result rather than crashing.

### 1. Evidence (what happened)

When you type a question, the system fetches real data from 8 sources in parallel:

- **Wikipedia** — background context on entities and events
- **DuckDuckGo** — live web search for recent news
- **FRED** — Federal Reserve economic data (interest rates, housing, unemployment)
- **World Bank** — GDP, inflation, development indicators by country
- **GDELT** — global event database, 250M+ news articles
- **ReliefWeb** — humanitarian situation reports
- **Open-Meteo** — weather and climate data by location
- **ACLED** — armed conflict event data (requires free registration)

All fetchers run concurrently with a 5-second timeout. If a source fails, the others continue. The evidence is used to score relevance and inform the causal DAG.

### 2. Graph (what connects to what)

The system builds a directed acyclic graph (DAG) of causal relationships. For each domain (geopolitics, economics, climate, etc.) there's a template DAG based on established causal relationships from the literature.

When evidence is available, the template is enriched with event-specific nodes and edges. When Neo4j is running, the graph is persisted and reused across analyses.

Each edge in the graph has:
- `strength_score` — how strongly A causes B (0-1)
- `latency_hours` — typical time delay between cause and effect
- `confidence_interval` — uncertainty range
- `evidence_path` — which sources support this edge

### 3. Simulation (what actually changed)

The core of the system is a parallel agent-based simulation using [Mesa](https://mesa.readthedocs.io/).

**Timeline A** — the event happens. Agents receive the event signal and react according to their behavioral profiles.

**Timeline B** — the counterfactual. Same agents, same starting conditions, no event signal.

The diff `A(t) - B(t)` at each timestep is the true causal impact — isolated from baseline trends.

Agents are domain-specific. For a geopolitical event, you get: Energy Trader, OPEC, Diplomat, Refugee Population, Insurance Market, Central Bank. For a tech event: Venture Capitalist, Tech Competitor, Regulator, Labor Market.

Each agent has:
- **Triggers** — conditions that activate the agent (e.g., `conflict_intensity > 0.3`)
- **Reaction functions** — mathematical formulas (linear, exponential, sigmoid, step) that determine how the agent changes environment variables
- **Lag steps** — how many simulation steps before the reaction kicks in (maps to real-world hours)

The simulation runs 96 steps (96 hours) in ~0.01 seconds. No LLM calls during simulation — it's pure math.

### 4. Causal math (what we can prove)

After simulation, the `CausalLogExtractor` processes the simulation log to build the final causal chain:

1. Groups log entries by variable changed
2. Computes divergence between Timeline A and B for each variable
3. Finds the first step where divergence exceeds 2% threshold
4. Assigns each hop to the agent responsible
5. Calculates magnitude (normalized effect size) and persistence (fraction of steps where effect is significant)
6. Detects feedback loops via DFS on the hop graph

The result is a `SimulationCausalChain` — ordered hops, each with: agent, variable, mechanism, timing, magnitude, confidence.

---

## What makes this different from ChatGPT

ChatGPT will tell you that "Fed rate hikes affect mortgage rates." That's a first-order effect and it's in every textbook.

butterfly-effect runs a simulation. It doesn't retrieve text about what might happen — it models what actually happens when agents with specific behavioral profiles react to a specific signal. The 4th-order effect (construction job losses 30 days after a rate hike) isn't in any training data as a connected chain — it emerges from the simulation.

The other difference is falsifiability. Every hop in the chain has a confidence score derived from the simulation divergence, not from how confidently the LLM writes. A 0.54 confidence score means the simulation showed weak divergence — the effect is real but uncertain. ChatGPT doesn't know what it doesn't know.

---

## What makes this different from Bloomberg / Palantir

Bloomberg shows you what's happening. Palantir shows you patterns in historical data.

butterfly-effect shows you the causal mechanism — not correlation, not pattern matching, but the structural chain that connects cause to effect. It answers "why" and "how long until."

The counterfactual engine is the key difference. By running Timeline B (no event), we isolate the true causal impact from baseline trends. If housing starts were already declining before the rate hike, the simulation captures that — the counterfactual delta shows only the incremental effect of the event.

Bloomberg can show you that housing starts fell after the rate hike. butterfly-effect can show you that 247k of that decline was caused by the rate hike specifically, with a 168-hour lag, via the mortgage rate transmission mechanism.

---

## Validation methodology

We use 4 layers to ensure causal claims aren't just correlations:

**Layer 1: Divergence threshold**
A hop only appears in the chain if Timeline A diverges from Timeline B by more than 2%. This filters out noise and baseline variation.

**Layer 2: Confidence scoring**
Each hop's confidence is derived from: log entry count (more agent reactions = more confident), magnitude (larger effect = more confident), and persistence (longer-lasting effect = more confident). Not from LLM confidence.

**Layer 3: Historical backtesting**
The Fed 2022 rate cycle is our primary validation case. The system's predicted chain (Treasury yields → mortgage rates → housing starts → construction jobs) matches the actual FRED data within ±20% on timing and magnitude. See `backend/scripts/validate_fed_2022.py`.

**Layer 4: Refutation tests**
For the Fed 2022 case, we run the simulation with a placebo event (random noise instead of the rate hike) and verify the chain doesn't appear. This is the same methodology used in academic causal inference (DoWhy refutation tests).

---

## Current limitations

**Be honest about these before using the system in production:**

1. **Agent templates are hand-crafted.** The behavioral profiles in `dynamic_agents.py` are based on economic literature and domain knowledge, not learned from data. They're reasonable approximations, not ground truth.

2. **96 simulation steps = 96 hours.** Long-term effects (months, years) are extrapolated from short-term dynamics. The 4th-order effects shown in examples are directionally correct but timing estimates get less reliable beyond 30 days.

3. **No database = no persistence.** Without Neo4j and Postgres running, the graph is rebuilt from scratch for every analysis. This means no learning from previous analyses and no cross-event relationship building.

4. **LLM parsing can misclassify domains.** If Gemini/Mistral misidentifies the domain (e.g., classifying a financial event as "technology"), the wrong agent pool is used and the chain will be wrong. The keyword fallback in `_synthetic_event()` is a safety net but not perfect.

5. **Evidence quality varies.** DuckDuckGo and Wikipedia are good for context but not for quantitative data. FRED is excellent for US economic data but has no coverage of most countries. The system is strongest for US/EU economic and geopolitical events.

6. **Feedback loops are detected but not modeled.** The system identifies cycles in the causal graph but doesn't simulate them — it would require a different simulation architecture to handle circular causality properly.
