"""Validation: 2021 Texas Winter Storm (ERCOT failure).

Ground truth from Texas Legislature post-mortem reports.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from butterfly.causal.counterfactual import CounterfactualEngine

FIXTURE = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "texas_storm_2021.json").read_text()
)

GROUND_TRUTH = FIXTURE["ground_truth"]
TOLERANCE = 0.20


async def run() -> dict:
    engine = CounterfactualEngine()

    result = await engine.run_counterfactual(
        event_id=FIXTURE["event"]["event_id"],
        horizon_hours=2160,
        baseline_data=FIXTURE["baseline"],
        treatment_deltas=FIXTURE["treatment_deltas"],
    )

    checks = {}

    # Check 1: Natural gas price direction (should be strongly positive)
    natgas_diff = result.diff.get("NATGAS", [])
    if natgas_diff:
        peak = max(natgas_diff, key=abs)
        pct_change = (peak / FIXTURE["baseline"]["NATGAS"]) * 100
        expected = GROUND_TRUTH["natural_gas_price_pct_change"]
        error = abs(pct_change - expected) / abs(expected)
        checks["natural_gas_direction"] = {
            "our_pct": round(pct_change, 1),
            "expected_pct": expected,
            "error_pct": round(error * 100, 1),
            "passed": error <= TOLERANCE,
        }

    # Check 2: Manufacturing output direction (should be negative)
    mfg_diff = result.diff.get("MANUFACTURING", [])
    if mfg_diff:
        peak = min(mfg_diff)  # Most negative
        pct_change = (peak / FIXTURE["baseline"]["MANUFACTURING"]) * 100
        expected = GROUND_TRUTH["manufacturing_output_pct_change"]
        error = abs(pct_change - expected) / abs(expected)
        checks["manufacturing_direction"] = {
            "our_pct": round(pct_change, 1),
            "expected_pct": expected,
            "error_pct": round(error * 100, 1),
            "passed": error <= TOLERANCE,
        }

    # Check 3: Causal chain depth
    chain_depth = len(result.causal_edges)
    checks["chain_depth"] = {
        "depth": chain_depth,
        "minimum": GROUND_TRUTH["chain_depth_minimum"],
        "passed": chain_depth >= GROUND_TRUTH["chain_depth_minimum"],
    }

    passed = sum(1 for c in checks.values() if c.get("passed", False))
    total = len(checks)

    return {
        "scenario": FIXTURE["scenario"],
        "checks": checks,
        "passed": passed,
        "total": total,
        "overall_pass": passed >= 2,
    }


if __name__ == "__main__":
    result = asyncio.run(run())
    print(f"\n{result['scenario']}")
    for name, check in result["checks"].items():
        status = "PASS" if check.get("passed") else "FAIL"
        print(f"  {status}  {name}: {check}")
    print(f"\n{result['passed']}/{result['total']} checks passed")
    print("PASS" if result["overall_pass"] else "FAIL")
