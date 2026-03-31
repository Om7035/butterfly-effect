# How butterfly-effect works

For people who want to understand the internals before contributing or building on top of it.

---

## The 4 ingredients

### 1. Data

When you type a question, 8 evidence sources are queried in parallel with a 5-second timeout each:

| Source | What it provides | Key |
|--------|-----------------|-----|
| Wikipedia | Background context, entity definitions | None |
| DuckDuckGo | Live web search, recent news | None |
| FRED | US economic time-series (rates, housing, unemployment) | Free |
| World Bank | GDP, inflation, development indicators by country | None |
| GDELT | 250M+ global news events database | None |
| ReliefWeb | Humanitarian situation reports | None |
| Open-Meteo | Weather and climate data by location | None |
| ACLED | Armed conflict event data | Free (OAuth2) |

All fetchers run concurrently. If one fails, the others continue. Evidence is scored for relevance by checking how many primary actors appear in the content.

### 2. Graph

The system builds a directed acyclic graph (DAG) of causal relationships. For each domain, there's a template DAG validated against academic literature:

- **Finance** â€” Bernanke (2005) monetary transmission mechanism
- **Geopolitics** â€” Collier & Hoeffler (2004) conflict economics
- **Climate** â€” IPCC AR6 (2021) impact pathways
- **Health** â€” Ferguson et al. (2020), Eichenbaum et al. (2021)
- **Technology** â€” Brynjolfsson & McAfee (2014) second machine age

Each edge carries: `strength_score`, `latency_hours`, `confidence_interval`, and a plain-English `mechanism` description.

When Neo4j is running, the graph is enriched with event-specific edges from the knowledge base. Without Neo4j, the template is used directly (bootstrap mode).

Cycle detection uses DFS. When a cycle is found, the weakest edge (lowest confidence) is removed iteratively until the graph is acyclic.

### 3. Agents

The core of the system is a parallel agent-based simulation using [Mesa](https://mesa.readthedocs.io/).

**Timeline A** â€” the event happens. Agents receive the event signal and react.

**Timeline B** â€” the counterfactual. Same agents, same starting conditions, no event signal.

The diff `A(t) - B(t)` at each timestep is the true causal impact â€” isolated from baseline trends.

Each agent has:

```python
BehaviorProfile(
    agent_name="Energy Trader",
    agent_type="market",
    domain="geopolitics",
    triggers=[
        TriggerRule(variable="conflict_intensity", operator=">", threshold=0.3)
    ],
    reaction_functions=[
        ReactionFn(
            target_variable="oil_price",
            formula="exponential",   # linear | exponential | step | sigmoid
            magnitude=8.0,
            direction=1,
            lag_steps=1,             # 1 step = 1 hour
        )
    ],
    dampening_factor=0.85,
)
```

The simulation runs 96 steps (96 hours) in ~0.01 seconds. No LLM calls during simulation â€” pure math.

### 4. Causal reasoning

After simulation, `CausalLogExtractor` processes the log into an ordered chain:

1. Groups log entries by `variable_changed`
2. Computes `diff_series[var][step] = A(step, var) - B(step, var)`
3. Finds `step_triggered` â€” first step where `|diff| > 2%` (divergence threshold)
4. Assigns each hop to the responsible agent
5. Scores confidence: `0.4 Ã— log_count + 0.4 Ã— magnitude + 0.2 Ã— persistence`
6. Detects feedback loops via NetworkX `simple_cycles`
7. Infers domain coverage from variable names

Hops are sorted by `step_triggered` â€” this is the causal order.

---

## Why not just use ChatGPT?

ChatGPT will tell you that "Fed rate hikes affect mortgage rates." That's a first-order effect and it's in every textbook.

butterfly-effect runs a simulation. It doesn't retrieve text about what might happen â€” it models what actually happens when agents with specific behavioral profiles react to a specific signal. The 4th-order effect (construction job losses 30 days after a rate hike) isn't in any training data as a connected chain â€” it emerges from the simulation.

The other difference is falsifiability. Every hop has a confidence score derived from simulation divergence, not from how confidently the LLM writes. A 0.54 confidence score means the simulation showed weak divergence â€” the effect is real but uncertain. ChatGPT doesn't know what it doesn't know.

---

## Why not Bloomberg / Palantir?

Bloomberg shows you what's happening. Palantir shows you patterns in historical data.

butterfly-effect shows you the causal mechanism â€” not correlation, not pattern matching, but the structural chain that connects cause to effect with timing.

The counterfactual engine is the key difference. By running Timeline B (no event), we isolate the true causal impact from baseline trends. If housing starts were already declining before the rate hike, the simulation captures that â€” the counterfactual delta shows only the incremental effect of the event.

Bloomberg can show you that housing starts fell after the rate hike. butterfly-effect can show you that 247k of that decline was caused by the rate hike specifically, with a 168-hour lag, via the mortgage rate transmission mechanism.

---

## Validation methodology

Four layers:

**Layer 1 â€” Divergence threshold**
A hop only appears in the chain if Timeline A diverges from Timeline B by more than 2%. This filters out noise and baseline variation.

**Layer 2 â€” Confidence scoring**
Each hop's confidence is derived from: log entry count (more agent reactions = more confident), magnitude (larger effect = more confident), and persistence (longer-lasting = more confident). Not from LLM confidence.

**Layer 3 â€” Historical backtesting**
The Fed 2022 rate cycle is the primary validation case. The system's predicted chain (Treasury yields â†’ mortgage rates â†’ housing starts â†’ construction jobs) matches actual FRED data within Â±20% on timing and magnitude. See `backend/scripts/validate_fed_2022.py`.

**Layer 4 â€” Refutation tests**
When DoWhy is available, three automated refutation tests run:
- **Random common cause** â€” adds a random confounder; effect should be stable
- **Placebo treatment** â€” permutes the treatment; effect should disappear
- **Data subset** â€” re-estimates on 80% of data; effect should be stable (Â±20%)

For aggregate-level events, the synthetic control method (Abadie & Gardeazabal 2003) constructs a weighted combination of control units and validates via in-space placebo tests. A result is only marked `is_trustworthy=True` if pre-treatment fit RÂ² â‰¥ 0.80.

---

## Current limitations

Be honest about these before using in production:

**1. Agent templates are hand-crafted.**
The behavioral profiles in `dynamic_agents.py` are based on economic literature and domain knowledge, not learned from data. They're reasonable approximations, not ground truth.

**2. 96 simulation steps = 96 hours.**
Long-term effects (months, years) are extrapolated from short-term dynamics. The 4th-order effects shown in examples are directionally correct but timing estimates get less reliable beyond 30 days.

**3. No database = no persistence.**
Without Neo4j and Postgres running, the graph is rebuilt from scratch for every analysis. No learning from previous analyses, no cross-event relationship building.

**4. LLM parsing can misclassify domains.**
If Gemini/Mistral misidentifies the domain (e.g., classifying a financial event as "technology"), the wrong agent pool is used and the chain will be wrong. The keyword fallback is a safety net but not perfect.

**5. Evidence quality varies.**
DuckDuckGo and Wikipedia are good for context but not for quantitative data. FRED is excellent for US economic data but has no coverage of most countries. The system is strongest for US/EU economic and geopolitical events.

**6. Feedback loops are detected but not simulated.**
The system identifies cycles in the causal graph but doesn't simulate them â€” it would require a different simulation architecture to handle circular causality properly.
