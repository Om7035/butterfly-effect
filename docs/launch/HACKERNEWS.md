# Show HN: butterfly-effect – type any event, see the causal chain nobody else sees

**Title:** Show HN: butterfly-effect – type any event, see the causal chain nobody else sees

**URL:** https://github.com/Om7035/butterfly-effect

---

**Post body:**

I built this because I kept noticing that smart people — analysts, journalists, policymakers — would correctly identify a first-order effect and then stop. The Fed raises rates, mortgage rates go up, done. But the chain doesn't stop there.

butterfly-effect is an open-source causal chain engine. You type any event in plain English. It runs two parallel agent-based simulations (event vs. no-event), diffs them, and shows you the full cascade — out to the 4th and 5th order — with timing and confidence scores.

**The example that made me build this:**

When Hamas attacked Israel on October 7, 2023, every analyst immediately talked about oil prices. That's hop 2. What nobody was talking about in October 2023 was hop 6: the ECB's September 2023 "mission accomplished" on inflation was about to be invalidated — via Red Sea shipping disruptions → EU LNG prices → energy inflation re-acceleration. That showed up in Eurostat data in Q1 2024. The chain was traceable from day one.

**How it works:**

1. LLM (Gemini/Mistral, free tier) parses your question into structured domains and actors
2. Evidence fetched in parallel from Wikipedia, FRED, DuckDuckGo, World Bank, GDELT, ReliefWeb
3. Domain-specific agent templates (Energy Trader, OPEC, Diplomat, etc.) run in Mesa ABM
4. Timeline A (event) vs Timeline B (no event) — diff is the true causal impact
5. CausalLogExtractor orders hops by step_triggered, infers domains, scores confidence

**What it's not:**

It's not a prediction engine. It doesn't tell you what will happen. It shows you the structural chain that's already in motion — the one that's provable from the simulation divergence, not from LLM confidence.

It's also not a chatbot wrapper. The simulation runs in ~0.01 seconds. The LLM is used once at parse time and once for insights. Everything in between is pure math.

**Quickstart (no Docker, no database required):**

```bash
git clone https://github.com/Om7035/butterfly-effect.git
cd butterfly-effect/backend
pip install fastapi uvicorn pydantic-settings loguru httpx google-genai networkx mesa
# Add GEMINI_API_KEY to backend/.env (free at aistudio.google.com)
python -m uvicorn butterfly.main:app --port 8000
```

Then `cd frontend && npm install && npm run dev` and go to localhost:3000.

**Current limitations (being honest):**

- Agent behavioral profiles are hand-crafted, not learned from data
- Strongest for US/EU economic and geopolitical events
- Long-term effects (months+) are extrapolated, not simulated
- No database = no persistence between analyses

**What I'm looking for:**

- People who find a wrong causal chain — open an issue with the question and what was wrong
- Domain experts who want to add new agent templates (cryptocurrency, real estate, etc.)
- Anyone who has a question they want to trace that the current domains don't cover well

The EXAMPLES.md has 10 worked examples across different domains if you want to see what it produces before running it.

MIT license. Built in Python + Next.js.
