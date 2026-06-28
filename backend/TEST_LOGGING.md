# Backend Logging Integration Test

## Quick Test: Run Server & Make Request

```bash
# Terminal 1: Start the server
cd backend
python -m uvicorn butterfly.main:app --reload

# Terminal 2: Make a test request
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the cascading effects of Fed rate hikes?"}' \
  --no-buffer

# Watch Terminal 1 for comprehensive logs showing:
# - Stage transitions (PARSE → FETCH → GRAPH → SIMULATE → INSIGHTS)
# - Timing for each operation
# - Data source results (Universal Fetcher, FRED, GDELT)
# - Graph building stats (nodes, edges, hops)
# - Agent simulation progress
# - Insight generation and SNN verification
```

## Expected Log Output

You should see colorized terminal output like:

```
[15:42:30.123] INFO    | butterfly:startup:67     | butterfly-effect startup complete

[15:42:35.456] INFO    | analyze:analyze:830      | 🚀 ANALYZE REQUEST | question='What are the cascading effects of Fed rate hikes?'...
[15:42:35.457] INFO    | analyze:analyze_stream:473 | ▶️  STAGE [ANALYSIS] START | question_length=47

[15:42:35.458] INFO    | analyze:_analyze_stream:497 | ⏱️  START: LLM event parsing
[15:42:36.234] INFO    | analyze:_analyze_stream:505 | ✅ DONE: LLM event parsing (0.78s)
[15:42:36.235] INFO    | analyze:_analyze_stream:506 | ✅ STAGE [PARSE] DONE | title=Fed Raises Interest Rates | domains=2 | severity=major | causal_seeds=5

[15:42:36.236] INFO    | analyze:_analyze_stream:524 | ▶️  STAGE [FETCH] START
[15:42:36.237] INFO    | analyze:_analyze_stream:529 | ⏱️  START: Parallel evidence fetch (Universal, GDELT, FRED)
[15:42:36.239] INFO    | universal_fetcher:fetch:130 | 🔍 FETCHER Starting: domain=economics queries=1
[15:42:38.456] INFO    | universal_fetcher:fetch:160 | 📊 FETCHER 45 raw → 30 ranked (relevance-sorted)
[15:42:38.567] INFO    | analyze:_analyze_stream:538 | ✅ DONE: Parallel evidence fetch (Universal, GDELT, FRED) (2.33s)
[15:42:38.568] INFO    | analyze:_analyze_stream:539 | ✅ SUCCESS FETCH [UniversalFetcher   ] SUCCESS | items=30  |   2.33s
[15:42:38.569] INFO    | analyze:_analyze_stream:540 | ✅ SUCCESS FETCH [GDELT              ] SUCCESS | items=12  |   1.89s
[15:42:38.570] INFO    | analyze:_analyze_stream:541 | ✅ SUCCESS FETCH [FRED               ] SUCCESS | items=5   |   0.67s
[15:42:38.571] INFO    | analyze:_analyze_stream:548 | ✅ STAGE [FETCH] DONE | sources=3 | universal_items=30 | gdelt_items=12 | fred_series=5

[15:42:38.572] INFO    | analyze:_analyze_stream:566 | ▶️  STAGE [GRAPH] START
[15:42:38.573] INFO    | analyze:_analyze_stream:572 | ⏱️  START: Building base causal graph
[15:42:38.678] INFO    | analyze:_analyze_stream:580 | ✅ DONE: Building base causal graph (0.11s)
[15:42:38.679] DEBUG   | analyze:_analyze_stream:582 | 📊 Initial graph structure (dict with 3 keys):
[15:42:38.680] INFO    | analyze:_analyze_stream:592 | ⏱️  START: Applying evidence to graph
[15:42:39.012] INFO    | analyze:_analyze_stream:597 | ✅ DONE: Applying evidence to graph (0.34s)
[15:42:39.013] INFO    | analyze:_analyze_stream:598 | [ANALYZE] Evidence applied: 8 edges updated
[15:42:39.234] INFO    | analyze:_analyze_stream:610 | ⏱️  START: Waiting for deep causal parse
[15:42:39.456] INFO    | analyze:_analyze_stream:613 | ✅ DONE: Waiting for deep causal parse (0.22s)
[15:42:39.700] INFO    | analyze:_analyze_stream:635 | 📈 GRAPH BUILT | nodes=18 | edges=21 | max_hops=4 | 1.12s
[15:42:39.701] INFO    | analyze:_analyze_stream:636 | ✅ STAGE [GRAPH] DONE | nodes=18 | edges=21 | max_hop=4 | seconds=1.12

[15:42:39.702] INFO    | analyze:_analyze_stream:659 | ▶️  STAGE [SIMULATE] START
[15:42:39.703] INFO    | analyze:_analyze_stream:670 | ⏱️  START: Building DAG and computing C-Path scores
[15:42:39.890] INFO    | analyze:_analyze_stream:676 | ✅ DONE: Building DAG and computing C-Path scores (0.19s)
[15:42:39.891] INFO    | analyze:_analyze_stream:683 | ⏱️  START: Running universal hybrid simulation (168 steps)
[15:42:42.123] INFO    | analyze:_analyze_stream:689 | ✅ DONE: Running universal hybrid simulation (168 steps) (2.23s)
[15:42:42.124] INFO    | analyze:_analyze_stream:697 | 🎬 Simulation complete: 12 agents, 168 steps (hybrid)
[15:42:42.125] INFO    | analyze:_analyze_stream:699 | ✅ STAGE [SIMULATE] DONE | agents=12 | steps=168 | mode=hybrid | seconds=2.23

[15:42:42.126] INFO    | analyze:_analyze_stream:727 | ▶️  STAGE [INSIGHTS] START
[15:42:42.127] INFO    | analyze:_analyze_stream:739 | ⏱️  START: Extracting causal chain from simulation
[15:42:42.234] INFO    | analyze:_analyze_stream:742 | ✅ DONE: Extracting causal chain from simulation (0.11s)
[15:42:42.235] INFO    | analyze:_analyze_stream:745 | ⏱️  START: Generating LLM insights
[15:42:43.456] INFO    | analyze:_analyze_stream:747 | ✅ DONE: Generating LLM insights (1.22s)
[15:42:43.457] INFO    | analyze:_analyze_stream:748 | [ANALYZE] LLM generated 8 insights
[15:42:43.458] INFO    | analyze:_analyze_stream:752 | ⏱️  START: SNN verification gate
[15:42:43.678] INFO    | analyze:_analyze_stream:758 | ✅ DONE: SNN verification gate (0.22s)
[15:42:43.679] INFO    | analyze:_analyze_stream:769 | [SNN] {'total': 8, 'verified': 6, 'rejected': 2}
[15:42:43.680] INFO    | analyze:_analyze_stream:770 | ✅ STAGE [INSIGHTS] DONE | total=8 | verified=6 | rejected=2

[15:42:43.789] INFO    | analyze:_analyze_stream:795 | ✅ ANALYSIS COMPLETE | run_id=run_a1b2c3d4e5 | nodes=18 edges=21 insights=8 | agents=12 steps=168
```

## Log Files

All logs appear in the terminal with colors. To save to a file:

```bash
# Redirect to file
python -m uvicorn butterfly.main:app --reload 2>&1 | tee server.log

# Then search/grep:
grep "❌\|⚠️" server.log          # Errors/warnings
grep "STAGE \[" server.log        # Pipeline stages
grep "📊\|📈\|⏱️" server.log        # Key metrics
grep "FETCH" server.log            # Data fetching
```

## Testing Specific Endpoints

### Test 1: Basic Analyze Request
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "How did the 2008 financial crisis propagate?"}'
```

### Test 2: Economics Query
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the effects of quantitative easing?"}'
```

### Test 3: Geopolitical Query
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "How does trade war impact global markets?"}'
```

## Log Search Patterns

### Find all stage transitions:
```bash
grep "STAGE \[" server.log
```

### Find slowest operations:
```bash
grep "DONE:" server.log | grep -oE "\([0-9.]+s\)" | sort -t'(' -k2 -rn
```

### Find errors:
```bash
grep "❌\|ERROR" server.log
```

### Find data statistics:
```bash
grep "nodes=\|edges=\|items=" server.log
```

### See fetch performance:
```bash
grep "FETCH\|FETCHER" server.log
```

## Integration Points

Logging has been integrated into:

1. **Main Analyze Endpoint** (`api/analyze.py`)
   - Request start logging
   - Stage transitions with detailed metrics
   - Data fetching logs
   - Graph building progress
   - Simulation stats
   - Insight generation
   - Final completion summary

2. **Universal Fetcher** (`ingestion/universal_fetcher.py`)
   - Evidence fetch timing
   - Cache hit/miss
   - Result merging and ranking
   - Source quality weighting

3. **Worker/Celery** (`worker.py`)
   - Task lifecycle
   - Broker/backend configuration

4. **Main App Setup** (`main.py`)
   - Already initializes setup_logging()

## What to Look For

When running a query, you should see:

- ✅ All 5 stages completing (PARSE, FETCH, GRAPH, SIMULATE, INSIGHTS)
- ⏱️ Timing for each major operation
- 📊 Data counts (nodes, edges, insights, evidence items)
- 💾 Cache hits (if running same query twice)
- 🔍 Evidence fetcher starting and completing
- 📈 Graph stats showing causal depth (hops)
- 🎬 Agent simulation progress
- 🧪 SNN verification counts (verified vs rejected insights)

This gives complete visibility into the pipeline's behavior and performance!
