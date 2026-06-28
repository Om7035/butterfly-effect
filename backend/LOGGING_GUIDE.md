# Enhanced Logging & Debugging Guide

This guide shows how to use the new enhanced logging utilities across the butterfly-effect pipeline for easy debugging and real-time visibility.

## Quick Start

The logging is automatically initialized in `main.py`. When you run the server, you'll see colorized, timestamped logs.

```bash
python -m uvicorn butterfly.main:app --reload
```

## Log Output Format

```
[HH:mm:ss.SSS] LEVEL   | module:function:line | message
```

Example:
```
[14:23:45.123] INFO    | butterfly:startup:40 | ✅ DONE: Parsing event (0.45s)
[14:23:46.234] DEBUG   | analyze:_build_graph:52 | 📊 Evidence (dict with 8 keys):
[14:23:47.345] INFO    | analyze:_build_graph:218 | 📈 GRAPH BUILT | nodes=15 | edges=18 | max_hops=4 | 0.89s
```

## Integration Patterns

### 1. Timing Operations

Use `DebugTimer` to measure how long operations take:

```python
from butterfly.logging_utils import debug_timer, DebugTimer

# Method 1: Context manager (recommended)
with DebugTimer("Parsing event"):
    result = parse_event(question)

# Output:
# ⏱️  START: Parsing event
# ... your code ...
# ✅ DONE: Parsing event (0.45s)

# Method 2: Manual timing
timer = DebugTimer("Fetching evidence")
timer.__enter__()
try:
    evidence = fetch_evidence(event)
finally:
    timer.__exit__(None, None, None)
```

### 2. Logging Pipeline Stages

Use `log_stage()` to track pipeline progress:

```python
from butterfly.logging_utils import log_stage

log_stage("PARSE", "start")
log_stage("PARSE", "running")
log_stage("PARSE", "done", {"entities": 12, "events": 3})
log_stage("PARSE", "error", {"error": "NLP model unavailable"})

# Output:
# ▶️  STAGE [PARSE] START
# ⚙️  STAGE [PARSE] RUNNING
# ✅ STAGE [PARSE] DONE | entities=12 | events=3
# ❌ STAGE [PARSE] ERROR | error=NLP model unavailable
```

### 3. Logging Data Fetching

Use `log_fetch_result()` to track each data source:

```python
from butterfly.logging_utils import log_fetch_result
import time

for source in ["FRED", "GDELT", "Wikipedia", "NewsAPI"]:
    start = time.time()
    try:
        data = fetch_from(source)
        latency = time.time() - start
        log_fetch_result(source, success=True, count=len(data), latency=latency)
    except Exception as e:
        latency = time.time() - start
        log_fetch_result(source, success=False, count=0, latency=latency, error=str(e))

# Output:
# ✅ SUCCESS FETCH [FRED           ] SUCCESS | items=145 |  0.87s
# ✅ SUCCESS FETCH [GDELT          ] SUCCESS | items=342 |  1.23s
# ❌ FAILED  FETCH [Wikipedia      ] FAILED  | items=0   |  0.05s | error: Connection timeout
# ✅ SUCCESS FETCH [NewsAPI        ] SUCCESS | items=89  |  0.56s
```

### 4. Logging Graph Building

Use `log_graph_build()` for graph completion:

```python
from butterfly.logging_utils import log_graph_build
import time

start = time.time()
graph_data = build_graph(event, evidence)
elapsed = time.time() - start

log_graph_build(
    nodes=len(graph_data["nodes"]),
    edges=len(graph_data["edges"]),
    hops=max(n.get("hop", 0) for n in graph_data["nodes"]),
    elapsed=elapsed
)

# Output:
# 📈 GRAPH BUILT | nodes=18 | edges=21 | max_hops=4 | 0.89s
```

### 5. Logging Confidence Updates

Use `log_confidence_update()` for evidence-driven adjustments:

```python
from butterfly.logging_utils import log_confidence_update

old_conf = 0.65
new_conf = 0.78
log_confidence_update("housing_starts", old_conf, new_conf, "corroborated by FRED data")

# Output:
# 📈 CONFIDENCE [housing_starts    ] 0.65 → 0.78 (+0.13) | corroborated by FRED data
```

### 6. Logging Evidence Matching

Use `log_evidence_match()` for fine-grained debugging:

```python
from butterfly.logging_utils import log_evidence_match

for keyword_match in keyword_matches:
    log_evidence_match(
        node_id="fed_rate",
        source="FRED",
        keyword="interest rate",
        confidence_delta=0.12
    )

# Output:
# 🔍 EVIDENCE [fed_rate            ] FRED            keyword='interest rate' delta=+0.12
```

### 7. Progress Bars for Long Operations

Use `ProgressBar` for visibility into multi-item processing:

```python
from butterfly.logging_utils import ProgressBar

progress = ProgressBar(total=100, label="Backtesting cases")

for i, case in enumerate(test_cases):
    result = run_backtest(case)
    progress.update(1)

# Output:
# 📊 Backtesting cases: 10/100 (10%) | 5.2/s | ETA 17s
# 📊 Backtesting cases: 50/100 (50%) | 5.1/s | ETA 10s
# 📊 Backtesting cases: 100/100 (100%) ✅ | 19.6s total
```

### 8. Logging Data Samples for Debugging

Use `log_data_sample()` to inspect data structures:

```python
from butterfly.logging_utils import log_data_sample

evidence = fetch_evidence(event)
log_data_sample("Evidence fetched", evidence, max_items=3)

nodes = build_graph_nodes(event)
log_data_sample("Graph nodes", nodes, max_items=5)

# Output:
# 📊 Evidence fetched (dict with 8 keys):
#    FRED: {'count': 145, 'series': ['FEDFUNDS', 'UNRATE', 'HOUST']}
#    GDELT: {'count': 342, 'events': [...]}
#    Wikipedia: {'count': 89, 'articles': [...]}
#    ... and 5 more
# 📊 Graph nodes (list with 18 items):
#    [0] {'id': 'root', 'type': 'Event', 'label': 'Fed raises rates 100bps'}
#    [1] {'id': 'seed_0', 'type': 'Metric', 'label': 'Mortgage rates rise'}
#    ... and 16 more
```

## Example: Full Pipeline with Logging

Here's how to instrument a complete pipeline run:

```python
from butterfly.logging_utils import (
    DebugTimer, log_stage, log_fetch_result, log_graph_build,
    log_backtest_result, ProgressBar, log_data_sample
)
import time

async def analyze_with_logging(question: str) -> dict:
    """Full analysis pipeline with comprehensive logging."""
    
    # Stage 1: Parse
    with DebugTimer("Parsing event"):
        log_stage("PARSE", "start")
        event = parse_event(question)
        log_data_sample("Parsed event", event)
        log_stage("PARSE", "done", {"entities": len(event.entities)})
    
    # Stage 2: Fetch Evidence (parallel)
    log_stage("FETCH", "start")
    sources = ["FRED", "GDELT", "Wikipedia", "NewsAPI"]
    
    for source in sources:
        start = time.time()
        try:
            data = await fetch_from(source)
            log_fetch_result(source, True, len(data), time.time() - start)
        except Exception as e:
            log_fetch_result(source, False, 0, time.time() - start, str(e))
    
    log_stage("FETCH", "done")
    
    # Stage 3: Build Graph
    with DebugTimer("Building causal graph"):
        log_stage("GRAPH", "running")
        graph = build_graph(event, evidence)
        log_graph_build(
            len(graph["nodes"]), len(graph["edges"]),
            max(n.get("hop", 0) for n in graph["nodes"]),
            0.89
        )
        log_stage("GRAPH", "done")
    
    # Stage 4: Backtest
    log_stage("BACKTEST", "start")
    progress = ProgressBar(5, "Backtesting")
    
    for case in test_cases:
        result = run_backtest(case)
        log_backtest_result(case.name, 4, 4, 0.87, True)
        progress.update()
    
    log_stage("BACKTEST", "done")
    
    return graph

# Usage
result = await analyze_with_logging("Fed raises rates 100bps")
```

## Log Levels

Control log verbosity with `DEBUG`, `INFO`, `WARNING`, `ERROR`:

```bash
# Show all logs (default during development)
export LOG_LEVEL=DEBUG
python -m uvicorn butterfly.main:app --reload

# Show only important logs (production)
export LOG_LEVEL=INFO
python -m uvicorn butterfly.main:app
```

## Output Example: Real Run

```
[14:23:45.123] INFO    | butterfly:create_app:40  | ✅ DONE: spaCy model load (0.34s)
[14:23:45.456] INFO    | butterfly:startup:67     | butterfly-effect startup complete

[14:23:47.789] INFO    | analyze:analyze_stream:50 | ▶️  STAGE [PARSE] START
[14:23:48.012] DEBUG   | analyze:_parse_event:120 | 📊 Parsed event (dict with 6 keys):
[14:23:48.234] INFO    | analyze:analyze_stream:52 | ✅ STAGE [PARSE] DONE | entities=12 | events=3

[14:23:48.456] INFO    | analyze:analyze_stream:55 | ▶️  STAGE [FETCH] START
[14:23:48.678] INFO    | ingestion:fetch_from:80  | ✅ SUCCESS FETCH [FRED           ] SUCCESS | items=145 |  0.87s
[14:23:49.234] INFO    | ingestion:fetch_from:80  | ✅ SUCCESS FETCH [GDELT          ] SUCCESS | items=342 |  1.23s
[14:23:49.567] INFO    | ingestion:fetch_from:80  | ❌ FAILED  FETCH [Wikipedia      ] FAILED  | items=0   |  0.05s | error: Timeout
[14:23:50.123] INFO    | ingestion:fetch_from:80  | ✅ SUCCESS FETCH [NewsAPI        ] SUCCESS | items=89  |  0.56s
[14:23:50.345] INFO    | analyze:analyze_stream:65 | ✅ STAGE [FETCH] DONE

[14:23:50.456] INFO    | graph:_build_graph:100   | ⏱️  START: Building causal graph
[14:23:50.789] DEBUG   | graph:_build_graph:150   | 📊 Evidence nodes (dict with 3 keys):
[14:23:51.234] INFO    | graph:_build_graph:180   | 📈 GRAPH BUILT | nodes=18 | edges=21 | max_hops=4 | 0.78s
[14:23:51.345] INFO    | graph:_build_graph:100   | ✅ DONE: Building causal graph (0.89s)

[14:23:51.456] INFO    | backtesting:runner:150  | 🧪 BACKTEST [fed_rate_hike_june_2022    ] ✅ PASS | predicted=4 actual=4 | similarity=0.92
[14:23:52.234] INFO    | backtesting:runner:150  | 🧪 BACKTEST [svb_collapse_march_2023    ] ✅ PASS | predicted=4 actual=4 | similarity=0.88

[14:23:52.567] INFO    | analyze:analyze_stream:90 | ✅ STAGE [ANALYZE] DONE | confidence_avg=0.72
```

## Tips for Effective Debugging

1. **Search logs for errors**: `grep "❌\|⚠️" application.log`
2. **Track a specific source**: `grep "FRED" application.log`
3. **Monitor timing**: `grep "⏱️\|✅ DONE\|❌ FAILED" application.log`
4. **See data flow**: `grep "📊" application.log`
5. **Check confidence changes**: `grep "📈 CONFIDENCE" application.log`

## Adding Logging to Your Code

When adding new functionality:

1. Wrap operations with `DebugTimer` for performance visibility
2. Use `log_stage()` for each major pipeline step
3. Call `log_data_sample()` after major transformations
4. Log fetch operations with `log_fetch_result()`
5. Track confidence adjustments with `log_confidence_update()`

Example template:

```python
def my_new_function(input_data):
    from butterfly.logging_utils import DebugTimer, log_data_sample
    
    with DebugTimer("Processing input"):
        result = transform(input_data)
        log_data_sample("Transformed result", result)
    
    return result
```

That's it! The logging utilities handle the rest.
