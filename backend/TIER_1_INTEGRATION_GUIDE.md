# Tier 1 Integration Guide

How to wire calibration, alternative chains, and uncertainty propagation into the actual analysis pipeline.

---

## 1. Add Calibration to Analysis Results

**File:** `butterfly/api/analyze.py`

**Current:** Sends nodes, edges, insights only.

**Add:** Include calibration metadata when available.

```python
# At end of _analyze_stream, before sending result_payload:

from butterfly.backtesting.calibration import CalibrationAnalyzer

# If this is a known backtest case, compute calibration
calibration_metadata = None
if run_id in KNOWN_BACKTEST_CASES:
    analyzer = CalibrationAnalyzer()
    # Add predictions from this run
    for hop in chain.hops:
        analyzer.add_prediction(hop.confidence, hop_was_correct)
    analysis = analyzer.analyze()
    calibration_metadata = analysis.to_dict()

result_payload["calibration"] = calibration_metadata
yield _sse(result_payload)
```

**Frontend consumption:**
```typescript
// In page.tsx
if (result.calibration) {
  // Show calibration warning if miscalibrated
  if (result.calibration.mean_calibration_error > 0.2) {
    showWarning("Our confidence scores have ±20% error. Take with caution.");
  }
}
```

---

## 2. Integrate Alternative Chains

**File:** `butterfly/api/analyze.py`, `butterfly/extraction/graph_builder.py`

**Current:** Returns single chain in `result_payload["nodes"]` and `["edges"]`.

**Add:** Extract top-3 chains instead of top-1.

```python
# In _analyze_stream, after graph building:

from butterfly.backtesting.alternative_chains import AlternativeChainsBuilder

# Instead of selecting top-1 path:
chains = AlternativeChainsBuilder.extract_top_k_chains(graph, k=3)

# Send all 3 chains to frontend
result_payload["causal_chains"] = [
    {
        "rank": chain.rank,
        "hops": [h["id"] for h in chain.hops],  # Node IDs in order
        "description": chain.description,
        "cumulative_probability": round(chain.cumulative_probability, 2),
        "primary": (chain.rank == 1),
    }
    for chain in chains
]
```

**Frontend consumption:**
```typescript
// In ChainView.tsx
{result.causal_chains?.map(chain => (
  <div key={chain.rank} className={chain.primary ? "primary" : "alternative"}>
    <h3>{chain.description}</h3>
    <p>Chain probability: {(chain.cumulative_probability * 100).toFixed(0)}%</p>
    <div className="collapsed">Show chain path...</div>
  </div>
))}
```

---

## 3. Integrate Uncertainty Propagation

**File:** `butterfly/extraction/graph_builder.py` (where chain hops are assembled)

**Current:**
```python
chain_hops = [
    {"description": "...", "confidence": 0.85},
    {"description": "...", "confidence": 0.80},
]
```

**Change to:**
```python
from butterfly.backtesting.uncertainty_propagation import UncertaintyPropagator

# Build individual confidences as before
individual_confs = [
    ("Bond yields rise", 0.85),
    ("Mortgage rates increase", 0.80),
]

# Apply propagation
propagated = UncertaintyPropagator.propagate_chain(individual_confs)

# Now each hop has both:
chain_hops = [
    {
        "description": hop.description,
        "individual_confidence": hop.individual_confidence,
        "joint_confidence": hop.joint_confidence,
    }
    for hop in propagated
]
```

**Frontend consumption:**
```typescript
// In HopChainCard.tsx
<div className="confidence">
  <span className="individual">{(hop.individual_confidence * 100).toFixed(0)}% (this hop)</span>
  <span className="joint">{(hop.joint_confidence * 100).toFixed(0)}% (reaching here)</span>
</div>
```

---

## 4. Refusal Mechanism

**File:** `butterfly/api/analyze.py`

**Add before final yield:**
```python
# Compute chain quality metrics
max_confidence = max(n.get("confidence", 0) for n in graph["nodes"])
simulation_variance = esaa_stats.get("variance", 0)

if max_confidence < 0.5 or simulation_variance > 0.8:
    # Insufficient confidence
    yield _sse({
        "stage": "done",
        "status": "insufficient_confidence",
        "message": (
            "This event has too much uncertainty for confident causal prediction. "
            "Consider collecting more evidence before attempting analysis."
        ),
        "reason": (
            f"Low confidence ({max_confidence:.0%}) or high simulation variance ({simulation_variance:.1%}). "
            "Our template-based approach performs poorly on novel events."
        ),
        "recommendation": "Re-run once more data is available, or treat results as exploratory only.",
    })
    return
```

**Frontend consumption:**
```typescript
if (result.status === "insufficient_confidence") {
  return (
    <WarningBox>
      <h2>{result.message}</h2>
      <p>{result.reason}</p>
      <p className="recommendation">{result.recommendation}</p>
    </WarningBox>
  );
}
```

---

## 5. Add Harder Validation Cases

**File:** `butterfly/backtesting/cases.py`

**Add new cases:**
```python
BacktestCase(
    id="brexit_june_2016",
    event="UK votes to leave EU",
    date="2016-06-23",
    question="What are cascading effects of UK Brexit referendum?",
    known_outcomes=[
        KnownOutcome(
            hop=1,
            description="Sterling fell 10% against dollar within 24 hours",
            verified=True,
            source="OANDA FX historical data",
            timing_actual="hours",
            timing_expected_hours=2,
        ),
        KnownOutcome(
            hop=2,
            description="UK equity market dropped 3-5% (FTSE 100)",
            verified=True,
            source="London Stock Exchange",
            timing_actual="same day",
            timing_expected_hours=4,
        ),
        KnownOutcome(
            hop=3,
            description="Global markets experienced contagion selling",
            verified=True,
            source="NYSE, DAX, Nikkei reaction",
            timing_actual="next trading session",
            timing_expected_hours=24,
        ),
        # ... more hops
    ],
)
```

Then run calibration on all cases including new ones:
```bash
python -m butterfly.backtesting.calibration_runner
```

---

## 6. Update Brier Score Reporting

**Already integrated in:** `butterfly/backtesting/calibration.py`

**Add to analysis results:**
```python
result_payload["model_quality"] = {
    "brier_score": round(analysis.brier_score, 3),
    "brier_rating": (
        "EXCELLENT" if analysis.brier_score < 0.20 else
        "GOOD" if analysis.brier_score < 0.30 else
        "FAIR" if analysis.brier_score < 0.50 else
        "POOR"
    ),
    "calibration_error": round(analysis.mean_calibration_error, 3),
    "notes": "Brier score measures probabilistic forecast accuracy. Lower is better."
}
```

**Frontend:** Display in a "Model Quality" section
```typescript
<ModelQualityPanel>
  <div>Brier Score: {result.model_quality.brier_score} ({result.model_quality.brier_rating})</div>
  <div>Calibration Error: ±{(result.model_quality.calibration_error * 100).toFixed(1)}%</div>
</ModelQualityPanel>
```

---

## Integration Checklist

### Backend Changes
- [ ] Update `api/analyze.py` to compute and return:
  - [ ] Calibration metadata
  - [ ] Top-3 alternative chains
  - [ ] Chain with propagated uncertainty
  - [ ] Refusal triggers
  - [ ] Brier score
- [ ] Add 5 harder backtest cases to `backtesting/cases.py`
- [ ] Test with: `python -m butterfly.backtesting.calibration_runner`

### Frontend Changes
- [ ] Show alternative chains (collapsed by default, primary expanded)
- [ ] Display both individual + joint confidence for each hop
- [ ] Show refusal message when status="insufficient_confidence"
- [ ] Add Model Quality section with Brier score + calibration error
- [ ] Add "Calibration warning" banner if mean_calibration_error > 0.2

### Documentation Changes
- [ ] Update README with calibration statement
- [ ] Add "Limitations" section explaining templates
- [ ] Document refusal mechanism
- [ ] Publish sample calibration charts

### Validation
- [ ] Backtest on all cases (including hard ones)
- [ ] Generate and review calibration report
- [ ] Check uncertainty propagation math
- [ ] Test refusal trigger on novel events
- [ ] Manual QA: alternative chains visible and make sense

---

## Expected Result

When a user submits an analysis, they'll see:

```
PRIMARY ANALYSIS (highest probability chain)
├─ Hop 1: 90% → 90% joint confidence
├─ Hop 2: 85% → 76.5% joint confidence
├─ Hop 3: 75% → 57.4% joint confidence
└─ Chain probability: 57.4%

ALTERNATIVES (less likely but plausible)
├─ [collapsed] Alternative 1 (40% likely)
└─ [collapsed] Alternative 2 (15% likely)

MODEL QUALITY
├─ Calibration: Tool's 0.9-confidence predictions are 44% accurate (±46% error)
├─ Brier Score: 0.119 (EXCELLENT)
└─ Note: This tool's confidence scores are miscalibrated. Results should be treated as exploratory.
```

This communicates:
- ✅ Multiple futures are possible (not forced certainty)
- ✅ Compound uncertainty (chains get less likely deeper in)
- ✅ Honest calibration (admits when wrong)
- ✅ Scientific measurement (Brier score)
- ✅ Mature forecasting (transparent limitations)

---

## Timeline

**This week:** Backend integration (4-6 hours)
**Next week:** Frontend integration (6-8 hours)
**Then:** Validation on hard cases (4 hours)

Total: ~20 hours to full Tier 1 implementation + integration
