# butterfly-effect

A causal inference engine that makes invisible cascade effects visible, traceable, and quantifiable.

Run an event. Run the counterfactual (no event). Subtract. Show the *true causal chain* with confidence scores and evidence paths.

**Status:** Phase 1 & 2 Complete ✅ | Phase 3 In Progress 🔄

---

## 🧭 What is butterfly-effect?

A causal inference engine that makes invisible cascade effects visible, traceable, and quantifiable.

**Run an event. Run the counterfactual (no event). Subtract. Show the true causal chain with confidence scores and evidence paths.**

---

## ✨ Current Status

| Phase | Name | Status | Deliverables |
|-------|------|--------|--------------|
| 0 | Scaffolding | ✅ Complete | Docker, FastAPI, Config |
| 1 | Data Pipeline | ✅ Complete | FRED/GDELT ingesters, Celery, Event API |
| 2 | Knowledge Graph | ✅ Complete | spaCy NER, Relations, Neo4j graph |
| 3 | Causal Core | 🔄 In Progress | pgmpy DAG, DoWhy, Counterfactual |
| 4 | Simulation | ⏳ Planned | Mesa agents, Parallel runner |
| 5 | API Layer | ⏳ Planned | Full REST API |
| 6 | Frontend | ⏳ Planned | Dashboard, Visualizations |
| 7 | Validation | ⏳ Planned | Historical backtests |
| 8 | Launch | ⏳ Planned | GitHub release |

---

## 🛠️ Tech Stack

**Backend:** FastAPI, SQLAlchemy, Celery, spaCy, Neo4j, PostgreSQL, Redis  
**Frontend:** Next.js 14, TypeScript, Tailwind, Sigma.js, D3.js  
**Causal:** DoWhy, pgmpy, Mesa, statsmodels  
**Infrastructure:** Docker Compose, GitHub Actions
