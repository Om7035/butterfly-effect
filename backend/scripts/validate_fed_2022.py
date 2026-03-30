"""
Fed 2022 Rate Cycle Validation Script
======================================
Validates the counterfactual engine against known ground truth from the
2022 FOMC 75bps rate hike cycle.

Run with:
    python scripts/validate_fed_2022.py

Pass criteria: at least 2/3 metrics within ±20% of ground truth.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from butterfly.causal.counterfactual import CounterfactualEngine, FED_2022_BASELINE, FED_2022_TREATMENT_DELTA


# Ground truth from FRED + CBO published estimates
GROUND_TRUTH = {
    "MORTGAGE30US": {"delta": 1.93, "unit": "pp", "description": "30yr mortgage rate change"},
    "HOUST": {"delta": -247.0, "unit": "thousands", "description": "Housing starts change"},
    "UNRATE": {"delta": 0.23, "unit": "pp", "description": "Unemployment rate change"},
}

TOLERANCE_PCT = 0.20  # ±20%


async def run_validation():
    print("\nbutterfly-effect -- Fed 2022 Validation")
    print("=" * 60)

    engine = CounterfactualEngine()

    # Run counterfactual with Fed 2022 data
    result = await engine.run_counterfactual(
        event_id="fed_2022_hike",
        horizon_hours=2160,  # 90 days
        baseline_data=FED_2022_BASELINE.copy(),
        treatment_deltas=FED_2022_TREATMENT_DELTA.copy(),
    )

    print(f"\nTimeline generated: {len(result.timeline_a['FEDFUNDS'])} steps")
    print(f"Causal edges found: {len(result.causal_edges)}")
    print(f"Peak effects: {result.peak_delta_at_hours}")

    print("\n" + "-" * 60)
    print(f"{'Metric':<20} {'Our D':>10} {'Truth D':>10} {'Error':>10} {'Pass?':>8}")
    print("-" * 60)

    passes = 0
    total = 0

    for metric, truth in GROUND_TRUTH.items():
        if metric not in result.diff:
            print(f"{metric:<20} {'N/A':>10} {truth['delta']:>10.2f} {'N/A':>10} {'FAIL':>8}")
            total += 1
            continue

        # Get peak diff value
        diff_vals = result.diff[metric]
        our_delta = max(diff_vals, key=abs) if diff_vals else 0.0
        truth_delta = truth["delta"]

        if abs(truth_delta) > 1e-10:
            error_pct = abs(our_delta - truth_delta) / abs(truth_delta)
        else:
            error_pct = abs(our_delta)

        passed = error_pct <= TOLERANCE_PCT
        if passed:
            passes += 1
        total += 1

        status = "PASS" if passed else "FAIL"
        print(
            f"{metric:<20} {our_delta:>+10.3f} {truth_delta:>+10.3f} "
            f"{error_pct*100:>9.1f}% {status:>8}"
        )

    print("-" * 60)
    print(f"\nResult: {passes}/{total} metrics within +/-{int(TOLERANCE_PCT*100)}% of ground truth")

    # Check causal chain depth
    chain_depth = len(result.causal_edges)
    chain_pass = chain_depth >= 3
    print(f"Causal chain depth: {chain_depth} edges {'PASS' if chain_pass else 'FAIL'} (need >=3)")

    overall_pass = passes >= 2 and chain_pass
    print(f"\n{'PHASE 3 GATE PASSED' if overall_pass else 'PHASE 3 GATE FAILED'}")
    print("=" * 60)

    return overall_pass


if __name__ == "__main__":
    passed = asyncio.run(run_validation())
    sys.exit(0 if passed else 1)
