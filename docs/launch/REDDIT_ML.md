# Reddit r/MachineLearning post

**Title:** butterfly-effect: open-source causal chain engine using agent-based simulation + counterfactual diff — type any event, get 4th-order effects with confidence scores

---

**Post body:**

I've been working on an open-source system that combines agent-based modeling, counterfactual simulation, and causal chain extraction to answer: "This event just happened — what else will it affect, and when?"

**The technical approach:**

The core is a parallel simulation engine built on Mesa (Python ABM framework). For any input event:

1. **Domain classification** — Gemini/Mistral identifies domains (geopolitics, economics, climate, etc.) and primary actors
2. **Agent generation** — Domain-specific BehaviorProfiles are instantiated. Each agent has: TriggerRules (conditions that activate it), ReactionFunctions (linear/exponential/sigmoid/step formulas), and lag_steps (real-world reaction time)
3. **Parallel simulation** — Timeline A (event signal applied) and Timeline B (counterfactual baseline) run concurrently in a thread pool
4. **Causal extraction** — `CausalLogExtractor` processes the simulation log: groups by variable, computes A(t)-B(t) divergence, finds first step where divergence > 2% threshold, assigns hops to responsible agents

**Why not just use DoWhy/pgmpy directly?**

We do use causal DAG templates from the literature, but the simulation adds something that static DAGs can't: temporal dynamics. The question isn't just "does A cause B" but "when does A cause B, and how does the effect decay?" The Mesa simulation captures lag, dampening, and feedback in a way that a static DAG doesn't.

**The counterfactual diff is the key:**

```python
# Timeline A: event happens
model_a = UniversalModel(profiles=agents, event_signal={"conflict_intensity": 0.85})

# Timeline B: no event (same agents, same starting conditions)
model_b = UniversalModel(profiles=agents, event_signal=None)

# True causal impact at each timestep
diff = {var: {t: A[t][var] - B[t][var] for t in steps} for var in variables}
```

This isolates the event's causal contribution from baseline trends — the same logic as difference-in-differences, but running forward in simulation rather than backward on historical data.

**Confidence scoring:**

Each hop's confidence is derived from three components:
- `n_entries / 10` — more agent reactions = more confident (capped at 1.0)
- `magnitude` — normalized effect size: `|max_delta| / (|baseline| + |max_delta|)`
- `persistence` — fraction of steps where `|delta| > 1%`

Combined: `confidence = 0.4 * log_count + 0.4 * magnitude + 0.2 * persistence`

This is not LLM confidence — it's derived from simulation divergence.

**Validation:**

The Fed 2022 rate cycle is our primary validation case. The system's predicted chain (Treasury yields → mortgage rates → housing starts → construction jobs) matches FRED data within ±20% on timing and magnitude. The validation script is at `backend/scripts/validate_fed_2022.py`.

**What's missing / known limitations:**

- Agent behavioral profiles are hand-crafted (based on economic literature), not learned from data
- Feedback loops are detected but not simulated (would require different architecture)
- Long-term effects (months+) are extrapolated from short-term dynamics
- No learned causal discovery — we use template DAGs, not LINGAM or PC algorithm

**Stack:**

- Mesa (ABM) — agent simulation
- FastAPI — SSE streaming API
- Gemini/Mistral — event parsing and insight generation (free tier)
- FRED, World Bank, Wikipedia, DuckDuckGo, GDELT — evidence fetching
- React Flow + Framer Motion — visualization
- Next.js 14 — frontend

**Repo:** https://github.com/Om7035/butterfly-effect

MIT license. Happy to discuss the methodology — especially interested in feedback on the confidence scoring approach and whether there are better ways to handle the temporal dynamics.
