Let me read the actual code before answering anything.

Good. Now I have the full accurate picture of what's actually in the codebase. Here's the honest breakdown:

---

## What the engine actually does, algorithm by algorithm

### 1. Data Ingestion — parallel evidence gathering

Eight sources fire concurrently, each with a 5-second timeout:

- **GDELT** — queries the global news database by theme (`ECON_TRADE`, `GEOPOLITICS`, `PROTEST`, etc.). Each article comes back with a **Goldstein scale** score (−10 to +10, measures conflict/cooperation intensity) and a **CAMEO event code** (a 2-digit taxonomy of what happened — protest, threat, assault, sanctions). Articles outside the significance thresholds (Goldstein < −3 or > +5) are filtered out as noise.

- **FRED** — polls 5 US economic time-series (fed funds rate, mortgage rate, housing starts, unemployment, yield curve spread). Only emits an event when the value actually changed since last check — delta detection, not polling.

- **Wikidata SPARQL** — queries three causal properties directly: `P1542` (has effect), `P1536` (immediate cause of), `P828` (has cause). These are human-verified edges. Resolves entity names to QIDs first, then follows up to 2 hops deep. Results cached 24h since Wikidata is stable.

- **Wikipedia, DuckDuckGo, World Bank, ReliefWeb, Open-Meteo, ACLED, OpenAlex, RSS** — all via raw httpx, domain-routed based on the event type.

All network calls on GDELT and Wikidata use **tenacity** retry logic: 3 attempts, exponential backoff 1s → 4s, only on `TimeoutException` and `NetworkError`.

---

### 2. Named Entity Recognition — `extraction/ner.py`

Three-layer extraction:

**Layer 1 — spaCy NER** (transformer or small model): Runs the text through a pre-trained model, maps spaCy labels to internal types:
- `ORG`, `GPE`, `PERSON` → `Entity`
- `MONEY`, `PERCENT` → `Metric`
- `LAW` → `Policy`
- `EVENT` → `Event`

Confidence is heuristic by label type (ORG = 0.95, EVENT = 0.75, etc.) since spaCy doesn't give per-entity scores.

Deduplication: keeps highest-confidence entity per `(text.lower(), label)` pair.

**Layer 2 — Temporal parsing** (`dateparser` + regex fallback): Converts relative time expressions in article text into concrete datetimes. "Two weeks after the incident" → `reference_date + 14 days`. This feeds directly into `latency_hours` on causal graph edges. Without this, all edges get a flat domain-default latency (48h), which loses the timing signal entirely.

---

### 3. Relation Extraction — `extraction/relations.py`

Two strategies run in sequence, results merged and filtered at confidence ≥ 0.4:

**Strategy A — Causal pattern matching**: 10 regex patterns against the raw text:
```
"X caused Y"      → CAUSES    (0.95)
"X led to Y"      → CAUSES    (0.90)
"X triggered Y"   → TRIGGERS  (0.95)
"X drove Y"       → INFLUENCES (0.85)
"due to X, Y"     → CAUSES    (0.85)
...
```
When a pattern matches, it looks up both captured words in the entity list (exact match first, then partial). Only creates a relation if both sides resolve to known entities.

**Strategy B — Proximity + directional verbs**: For every pair of entities within 500 characters of each other, checks if a directional verb (`increase`, `fall`, `expand`, `worsen`, etc.) appears between them. If yes → `CORRELATES_WITH` at 0.5 confidence. This catches relationships the regex patterns miss.

---

### 4. CAMEO Escalation Chain Detection — `ingestion/gdelt.py`

This is the core butterfly-effect algorithm for geopolitical events:

1. Fetch all CAMEO-coded events for an actor over N days
2. Split into tier-1/2 (low signal: protests, threats, demands) and tier-3 (high signal: assault, sanctions, conflict)
3. For every tier-3 event, find all tier-1/2 events that preceded it within 90 days
4. Each matching pair becomes a candidate causal chain with:
   ```
   confidence = max(0.4, 0.9 - gap_days / 100)
   ```
   So a protest 5 days before a conflict scores 0.85. The same protest 80 days before scores 0.50. Confidence decays linearly with time gap.

The `CAMEO_ESCALATION_MAP` encodes known escalation pathways:
- Protest (14) → `ESCALATES_TO`
- Threat (13) → `ESCALATES_TO`
- Reduce relations (16) → `CAUSES` (sanctions)
- Coerce (17) → `CAUSES` (conflict)

---

### 5. Graph Building — `extraction/graph_builder.py`

Two-phase construction:

**Phase 1 — Wikidata seeding**: Before any NER runs, queries Wikidata for the event title and inserts verified causal edges at confidence 0.95. These become the high-confidence backbone of the graph.

**Phase 2 — NER/relation overlay**: Upserts entity nodes and relation edges from the extraction layer. Uses Cypher `MERGE` so repeated mentions increment `mention_count` rather than creating duplicates. Each edge stores `evidence_paths` — the actual text snippets that support it.

Graph storage fallback chain: Neo4j → Kùzu (embedded, persistent) → NetworkX (in-memory, lost on restart).

---

### 6. What the output looks like

Every analysis produces a **causal chain** — an ordered sequence of nodes and edges:

```
Event (your input)
  └─[CAUSES, confidence: 0.90, latency: 2h]──► Effect A
       └─[TRIGGERS, confidence: 0.85, latency: 48h]──► Effect B
            └─[INFLUENCES, confidence: 0.72, latency: 168h]──► Effect C
```

Each edge carries:
- `relation_type` — CAUSES / TRIGGERS / INFLUENCES / ESCALATES_TO / CORRELATES_WITH / CAUSED_BY
- `confidence` — 0.0–1.0, sourced from: Wikidata (0.95), pattern match (0.80–0.95), proximity (0.50), CAMEO decay formula
- `latency_hours` — how long after the trigger event this effect appears, derived from temporal parsing or domain default
- `evidence` — the actual text or Wikidata property that supports the edge
- `mention_count` — how many independent sources corroborate this edge

The graph is queryable via Cypher pathfinding: "find all effects of event X within 5 hops" returns the full cascade.

---

### What's not yet in this version of the codebase

The files in this workspace are the earlier phase. The simulation layer (Mesa ABM, parallel timelines A vs B, synthetic control, DoWhy identification), the LLM orchestrator, and the full pipeline are in a later version of the project. What's here is the ingestion + extraction + graph foundation that everything else builds on.