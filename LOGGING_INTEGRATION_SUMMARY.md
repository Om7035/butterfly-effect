# Logging Integration Summary

## Overview

Comprehensive, real-time logging has been integrated throughout the butterfly-effect backend pipeline. The system now provides **live terminal visibility** into every major operation, making debugging and monitoring simple.

## Key Features

### 1. **Colorized, Timestamped Output**
- `[HH:mm:ss.SSS]` timestamps
- Color-coded log levels (INFO, DEBUG, WARNING, ERROR)
- File:function:line context for every log

### 2. **Pipeline Stage Tracking**
Five main stages, each with start/done/error transitions:
- **PARSE** — LLM event parsing (causal seeds, severity, domains)
- **FETCH** — Evidence gathering (Universal Fetcher, GDELT, FRED)
- **GRAPH** — Causal graph building (NLP extraction, evidence application)
- **SIMULATE** — Agent swarm simulation (168 time steps)
- **INSIGHTS** — LLM insight generation + SNN verification

### 3. **Operation Timing**
Every major operation is wrapped with timing measurements:
```
⏱️  START: Operation name
✅ DONE: Operation name (2.34s)
```

### 4. **Data Flow Visibility**
- Evidence fetch results (count + latency for each source)
- Graph statistics (nodes, edges, max hop depth)
- Agent simulation progress (agents, steps completed, mode)
- Insight generation counts (total, verified, rejected)

## Files Modified

### Backend
```
backend/butterfly/
├── main.py                          ✅ Initializes setup_logging()
├── logging_utils.py                 ✅ NEW — Logging infrastructure
├── api/
│   └── analyze.py                   ✅ Integrated at all 5 stages
├── ingestion/
│   └── universal_fetcher.py         ✅ Evidence fetch logging
└── worker.py                        ✅ Celery task logging

New Documentation:
├── LOGGING_GUIDE.md                 ✅ How-to guide for developers
└── TEST_LOGGING.md                  ✅ Testing instructions
```

## Example Log Output

When you run an analysis, you'll see comprehensive logs like:

```
[17:36:05.234] INFO    | analyze:analyze:830      | 🚀 ANALYZE REQUEST | question='How do interest rates...'

[17:36:05.235] INFO    | analyze:_analyze_stream:473 | ▶️  STAGE [PARSE] START
[17:36:05.236] INFO    | analyze:_analyze_stream:497 | ⏱️  START: LLM event parsing
[17:36:06.012] INFO    | analyze:_analyze_stream:505 | ✅ DONE: LLM event parsing (0.78s)
[17:36:06.013] INFO    | analyze:_analyze_stream:510 | ✅ STAGE [PARSE] DONE | title=Interest Rate... | domains=2 | severity=major | causal_seeds=5

[17:36:06.014] INFO    | analyze:_analyze_stream:514 | ▶️  STAGE [FETCH] START
[17:36:06.015] INFO    | analyze:_analyze_stream:529 | ⏱️  START: Parallel evidence fetch (Universal, GDELT, FRED)
[17:36:06.017] INFO    | universal_fetcher:fetch:130 | 🔍 FETCHER Starting: domain=economics queries=1
[17:36:08.234] INFO    | universal_fetcher:fetch:160 | 📊 FETCHER 45 raw → 30 ranked (relevance-sorted)
[17:36:08.345] INFO    | analyze:_analyze_stream:538 | ✅ DONE: Parallel evidence fetch (Universal, GDELT, FRED) (2.33s)
[17:36:08.346] INFO    | analyze:_analyze_stream:539 | ✅ SUCCESS FETCH [UniversalFetcher   ] SUCCESS | items=30  |   2.33s
[17:36:08.347] INFO    | analyze:_analyze_stream:540 | ✅ SUCCESS FETCH [GDELT              ] SUCCESS | items=12  |   1.89s
[17:36:08.348] INFO    | analyze:_analyze_stream:541 | ✅ SUCCESS FETCH [FRED               ] SUCCESS | items=5   |   0.67s
[17:36:08.349] INFO    | analyze:_analyze_stream:548 | ✅ STAGE [FETCH] DONE | sources=3 | universal_items=30 | gdelt_items=12 | fred_series=5

[17:36:08.350] INFO    | analyze:_analyze_stream:566 | ▶️  STAGE [GRAPH] START
[17:36:08.351] INFO    | analyze:_analyze_stream:572 | ⏱️  START: Building base causal graph
[17:36:08.456] INFO    | analyze:_analyze_stream:580 | ✅ DONE: Building base causal graph (0.11s)
[17:36:08.592] INFO    | analyze:_analyze_stream:592 | ⏱️  START: Applying evidence to graph
[17:36:08.926] INFO    | analyze:_analyze_stream:600 | ✅ DONE: Applying evidence to graph (0.34s)
[17:36:08.927] INFO    | analyze:_analyze_stream:598 | [ANALYZE] Evidence applied: 8 edges updated
[17:36:09.234] INFO    | analyze:_analyze_stream:636 | 📈 GRAPH BUILT | nodes=18 | edges=21 | max_hops=4 | 1.12s
[17:36:09.235] INFO    | analyze:_analyze_stream:637 | ✅ STAGE [GRAPH] DONE | nodes=18 | edges=21 | max_hop=4 | seconds=1.12

[17:36:09.236] INFO    | analyze:_analyze_stream:659 | ▶️  STAGE [SIMULATE] START
[17:36:09.237] INFO    | analyze:_analyze_stream:670 | ⏱️  START: Building DAG and computing C-Path scores
[17:36:09.424] INFO    | analyze:_analyze_stream:676 | ✅ DONE: Building DAG and computing C-Path scores (0.19s)
[17:36:09.425] INFO    | analyze:_analyze_stream:683 | ⏱️  START: Running universal hybrid simulation (168 steps)
[17:36:11.648] INFO    | analyze:_analyze_stream:689 | ✅ DONE: Running universal hybrid simulation (168 steps) (2.23s)
[17:36:11.649] INFO    | analyze:_analyze_stream:697 | 🎬 Simulation complete: 12 agents, 168 steps (hybrid)
[17:36:11.650] INFO    | analyze:_analyze_stream:699 | ✅ STAGE [SIMULATE] DONE | agents=12 | steps=168 | mode=hybrid | seconds=2.23

[17:36:11.651] INFO    | analyze:_analyze_stream:727 | ▶️  STAGE [INSIGHTS] START
[17:36:11.652] INFO    | analyze:_analyze_stream:739 | ⏱️  START: Extracting causal chain from simulation
[17:36:11.763] INFO    | analyze:_analyze_stream:742 | ✅ DONE: Extracting causal chain from simulation (0.11s)
[17:36:11.764] INFO    | analyze:_analyze_stream:745 | ⏱️  START: Generating LLM insights
[17:36:12.986] INFO    | analyze:_analyze_stream:747 | ✅ DONE: Generating LLM insights (1.22s)
[17:36:12.987] INFO    | analyze:_analyze_stream:748 | [ANALYZE] LLM generated 8 insights
[17:36:12.988] INFO    | analyze:_analyze_stream:752 | ⏱️  START: SNN verification gate
[17:36:13.210] INFO    | analyze:_analyze_stream:758 | ✅ DONE: SNN verification gate (0.22s)
[17:36:13.211] INFO    | analyze:_analyze_stream:769 | [SNN] {'total': 8, 'verified': 6, 'rejected': 2}
[17:36:13.212] INFO    | analyze:_analyze_stream:770 | ✅ STAGE [INSIGHTS] DONE | total=8 | verified=6 | rejected=2

[17:36:13.321] INFO    | analyze:_analyze_stream:795 | ✅ ANALYSIS COMPLETE | run_id=run_a1b2c3d4e5 | nodes=18 edges=21 insights=8 | agents=12 steps=168
```

## How to Use

### 1. Run the Server
```bash
cd backend
python -m uvicorn butterfly.main:app --reload
```

The logging is automatically initialized by `main.py`.

### 2. Make a Request
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "How do Fed rate hikes affect mortgage markets?"}'
```

### 3. Watch Terminal Output
Comprehensive logs stream in real-time showing:
- Stage progress with ✅ (done), ⏱️ (timing), 📊 (data), 🎬 (simulation)
- Operation timings for performance monitoring
- Data statistics (count of nodes, edges, evidence items)
- Error/warning messages for debugging

### 4. Save Logs (Optional)
```bash
# Redirect to file
python -m uvicorn butterfly.main:app --reload 2>&1 | tee server.log

# Search/filter logs
grep "STAGE \[" server.log        # See stage transitions
grep "❌\|⚠️" server.log            # See errors/warnings
grep "FETCH" server.log            # See data fetching
grep "seconds=" server.log         # See operation timings
```

## Logging Utilities Available

All in `butterfly/logging_utils.py`:

```python
# Timing context manager
with DebugTimer("Operation name"):
    # your code here

# Stage tracking
log_stage("STAGE_NAME", "start")
log_stage("STAGE_NAME", "done", {"key": value})
log_stage("STAGE_NAME", "error", {"error": "message"})

# Data fetching
log_fetch_result(source, success, count, latency, error=None)

# Graph building
log_graph_build(nodes, edges, hops, elapsed)

# Data samples (for debugging)
log_data_sample("label", data, max_items=3)

# Confidence updates
log_confidence_update(node_id, old_conf, new_conf, reason)

# Progress bars
progress = ProgressBar(total=100, label="Processing")
progress.update(1)  # increment
```

See `LOGGING_GUIDE.md` for detailed examples and patterns.

## Integration Points

Already integrated:
- ✅ `api/analyze.py` — Main pipeline (all 5 stages)
- ✅ `ingestion/universal_fetcher.py` — Evidence fetching
- ✅ `worker.py` — Celery task lifecycle
- ✅ `main.py` — App initialization

Ready to integrate into:
- `llm/event_parser.py` — LLM parsing details
- `causal/dag.py` — DAG building
- `simulation/universal_runner.py` — Simulation step details
- `backtesting/runner.py` — Test case results
- Additional data sources (FRED, GDELT, etc.)

## Control Log Verbosity

By environment variable or in `config.py`:

```python
# Show all logs (development)
settings.debug = True
# setup_logging(debug=True)  # → DEBUG level

# Show only important logs (production)
settings.debug = False
# setup_logging(debug=False) # → INFO level only
```

## Next Steps for Users

1. **Run the server**: `python -m uvicorn butterfly.main:app --reload`
2. **Make a request**: POST to `/api/v1/analyze`
3. **Watch the terminal** for real-time pipeline visibility
4. **Use grep/tail** to filter logs if needed
5. **Refer to LOGGING_GUIDE.md** for code examples if adding more logging

The logging system is production-ready and provides the complete debugging visibility you requested!
