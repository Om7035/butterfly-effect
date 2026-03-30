"""Validation: COVID Semiconductor Shortage (2021-2022).

Ground truth from academic literature and BLS/FRED data.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from butterfly.causal.counterfactual import CounterfactualEngine

FIXTURE = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "covid_supply_chain.json").read_text()
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

    # Check 1: Auto production direction (should be negative)
    auto_diff = result.diff.get("AUTO_PRODUCTION", [])
    if auto_diff:
        peak = min(auto_diff)
        pct_change = (peak / FIXTURE["baseline"]["AUTO_PRODUCTION"]) * 100
        expected = GROUND_TRUTH["auto_production_pct_change"]
        error = abs(pct_change - expected) / abs(expected)
        checks["auto_production"] = {
            "our_pct": round(pct_change, 1),
            "expected_pct": expected,
            "error_pct": round(error * 100, 1),
            "passed": error <= TOLERANCE,
        }

    # Check 2: Causal chain depth
    chain_depth = len(result.causal_edges)
    checks["chain_depth"] = {
        "depth": chain_depth,
        "minimum": GROUND_TRUTH["chain_depth_minimum"],
        "passed": chain_depth >= GROUND_TRUTH["chain_depth_minimum"],
    }

    # Check 3: Non-zero diff for at least 2 metrics
    nonzero = sum(
        1 for vals in result.diff.values()
        if vals and max(abs(v) for v in vals) > 0.01
    )
    checks["cascade_propagation"] = {
        "nonzero_metrics": nonzero,
        "passed": nonzero >= 2,
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
