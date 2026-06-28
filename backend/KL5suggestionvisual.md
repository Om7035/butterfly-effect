# Filtered Suggestions for butterfly-effect

## Worth Implementing (High ROI, Low Risk)

### Cross-Query Causal Memory (2h)
Store edges in SQLite. Boost confidence for repeated relationships (e.g., "Fed hike → mortgage up" seen 50x). Adds learning without retraining. File: `causal/dag.py`. Risk: stale relationships — solve with 90-day TTL.

### Surprise Score (2.5h)
Compare simulation delta vs FRED historical variance. Flag z>2.0 as "unusually large effect." Answers "is this normal?" File: `universal_runner.py`. Requires FRED_API_KEY.

### Cross-Domain Bridge Detection (2h)
Already planned. Mark nodes where cascade crosses domains. Visual: ⚡ icon. File: `dag.py`.

### Evidence Quality Scoring (2h)
Already planned. Weight by source authority + recency + readability. File: `universal_fetcher.py`.

### Graph Diff for Severity Slider (2h)
Already planned. Show "+3 nodes, -2 edges" when slider moves. File: `analyze.py` new endpoint.

### Causal Path Highlighting (2h)
Click node → highlight all ancestor/descendant edges. Makes dense graphs readable. File: `CausalGraphCanvas.tsx`. Zero new libraries.

### Graph Export to PNG (1.5h)
`html-to-image` library. "Download as Image" button. Analysts need this for reports. File: `GraphToolbar.tsx`.



### Dynamic Evidence Timeout by Domain (1h)
Economics queries prioritize FRED (2s), geopolitics prioritize GDELT (3s). Reduces avg latency 30%. File: `universal_fetcher.py`.

### Confidence Calibration via Platt Scaling (1.5h)
After 50 validations, fit logistic regression: raw CCI → calibrated probability. Makes scores interpretable. File: `cpath.py`. Requires validation data.

---

## Consider Later (Correct but Lower Priority)

### Wikipedia Pageview Trends (2.5h)
Fetch 30-day pageview trend for entities. Rising attention → increase severity multiplier. Interesting signal but marginal gain. File: `universal_fetcher.py`.

### Contradiction Detection in Evidence (3h)
Use NLI model to find evidence that contradicts edges. Flags "contested" edges. Adds nuance but requires 300MB model. File: `snn_gate.py`.

### Insight Deduplication via Embeddings (1h)
LLM generates 3 insights, keep only semantically distinct ones. Reduces clutter. File: `insight_generator.py`. Reuses sentence-transformers.

### Event Embedding for Similar Queries (2h)
"This is 78% similar to your 2024 'Trade War' simulation." Adds case-based reasoning. File: `analyze.py`. Requires 50+ past runs.

### Domain-Adaptive C-Path Alpha (1h)
Economics alpha=0.92, social=0.75. Reflects real decay rates. File: `cpath.py`. Needs validation to tune.

### Layered Graph with Domain Filtering (2h)
Toggle visibility by domain. "Show only economics" or "cross-domain only." File: `GraphToolbar.tsx`.

---

## Skip (Wrong Fit or Premature)

### LiteLLM for Fallback
Already have multi-provider routing. LiteLLM adds 50ms latency for no gain at current scale.

### orjson for SSE
Payload is <500KB. Standard json is fine. Premature optimization.

### igraph for C-Path
Graphs are 13-20 nodes. NetworkX is fast enough. igraph adds install complexity.

### agentpy vs Mesa
Mesa works. Switching frameworks for 40% speed gain on a 0.3s operation saves 0.12s. Not worth migration risk.

### numba JIT for Math Baseline
400ms → 200ms but adds LLVM dependency. Docker-only. Skip unless latency becomes critical.

### spaCy Transformer Model
500MB download, 1.5GB RAM, 10ms → 200ms per doc. Accuracy gain is real but cost is high. Current `en_core_web_sm` is adequate.

### Merkle Tree for ESAA
SHA-256 is sufficient. Merkle tree adds complexity for no user-facing benefit.

### OpenTelemetry Traces
Good for production debugging but not a user-facing feature. Add when scaling, not now.

### nx-cugraph GPU Acceleration
Requires NVIDIA GPU. Graphs are too small to benefit. Skip.

### Plotly for "What If" View
ReactFlow already handles this. Plotly adds bundle size for no UX gain.

### instructor for Structured Output
Gemini already uses `response_mime_type="application/json"`. instructor is redundant.

### Langfuse Monitoring
Good for production observability but not a feature. Add when scaling.

### rank_bm25 for Evidence Filtering
SNN gate already improved with semantic similarity. BM25 is redundant.

### Louvain Community Detection
Dagre hierarchical layout already groups by hop depth. Community detection would break causal ordering.

### Semaphore for Fetch Concurrency
Current `asyncio.gather` with 6s timeout works. Semaphore adds complexity for no gain at current scale.

---

## Viral/UX Suggestions (Separate from Technical)

### cmdk Command Palette (2h)
Cmd+K interface. Makes tool feel professional. File: `app/page.tsx`. Worth doing.

### MapLibre for Geographic Events (4h)
Show affected regions on map when `geographic_scope` present. Grounds simulation in reality. File: new `MapView.tsx`.

### "Parallel Universes" Split View
Show timeline_a (event happens) vs timeline_b (counterfactual) side-by-side. Powerful visual. File: `page.tsx`. 3h.

### D3-Force Layout
Skip. Breaks causal depth ordering. Dagre is correct for DAGs.

### Aceternity UI
Skip. Looks like marketing site, not a tool.

### River Plot / Stream Graph
Beautiful but requires restructured timeline data. Do after simulation improvements solid.

---

## Summary: Do These 10 First (Total: 18.5h)

1. Cross-query causal memory (2h)
2. Surprise score (2.5h)
3. Cross-domain bridge detection (2h)
4. Evidence quality scoring (2h)
5. Graph diff (2h)
6. Causal path highlighting (2h)
7. Graph export PNG (1.5h)
8. User feedback thumbs (2h)
9. Dynamic evidence timeout (1h)
10. Confidence calibration (1.5h)

All use existing stack or trivial libraries. All have clear user-facing value. All under 3h each.