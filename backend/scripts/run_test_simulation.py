"""Phase 4 gate: run 100-agent simulation and verify A != B.

Run with:
    python scripts/run_test_simulation.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from butterfly.simulation.runner import SimulationRunner


FED_2022_SIGNAL = {
    "event_id": "fed_2022_hike",
    "rate_delta": 0.75,
    "mortgage_delta": 1.93,
    "commodity_delta": 0.0,
}


async def main() -> bool:
    print("\nbutterfly-effect -- Phase 4 Simulation Test")
    print("=" * 55)
    print("Agents: 100 (50 market, 30 housing, 15 supply, 5 policy)")
    print("Steps:  168 (1 week hourly)")
    print("Running Timeline A (event) + Timeline B (counterfactual)...")

    runner = SimulationRunner()
    result = await runner.run_parallel(
        event_signal=FED_2022_SIGNAL,
        steps=168,
        n_market=50,
        n_housing=30,
        n_supply=15,
        n_policy=5,
    )

    print(f"\nSimulation complete in {result.duration_seconds:.1f}s")
    print(f"Steps completed: {result.steps_completed}")
    print(f"Agent log entries: {len(result.agent_logs)}")

    # Check Timeline A vs B diverge
    a_exposure = [
        v.get("avg_portfolio_exposure", 0)
        for v in result.timeline_a.values()
    ]
    b_exposure = [
        v.get("avg_portfolio_exposure", 0)
        for v in result.timeline_b.values()
    ]

    if a_exposure and b_exposure:
        a_final = a_exposure[-1]
        b_final = b_exposure[-1]
        diff = abs(a_final - b_final)
        print(f"\nTimeline A final portfolio_exposure: {a_final:.4f}")
        print(f"Timeline B final portfolio_exposure: {b_final:.4f}")
        print(f"Diff at final step: {diff:.4f}")
    else:
        diff = 0.0
        print("\nNo portfolio_exposure data collected")

    print("\n" + "-" * 55)
    checks = [
        ("Completes in <5 min", result.duration_seconds < 300),
        ("agent_logs non-empty", len(result.agent_logs) > 0),
        ("Timeline A != Timeline B", diff > 0.001),
        ("Steps completed = 168", result.steps_completed == 168),
    ]

    passed = 0
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}  {label}")
        if ok:
            passed += 1

    overall = passed == len(checks)
    print(f"\n{passed}/{len(checks)} checks passed")
    print("PHASE 4 GATE PASSED" if overall else "PHASE 4 GATE FAILED")
    print("=" * 55)
    return overall


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
