"""Phase 7 validation runner — all 3 historical scenarios.

Run with:
    python scripts/run_validation.py

Gate: at least 2/3 scenarios must pass.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from butterfly.causal.counterfactual import CounterfactualEngine, FED_2022_BASELINE, FED_2022_TREATMENT_DELTA

TOLERANCE = 0.20

# ── Scenario 1: Fed 2022 ──────────────────────────────────────────────────────

FED_GROUND_TRUTH = {
    "MORTGAGE30US": 1.93,
    "HOUST": -247.0,
    "UNRATE": 0.23,
}


async def validate_fed_2022() -> dict:
    engine = CounterfactualEngine()
    result = await engine.run_counterfactual(
        event_id="fed_2022_hike",
        horizon_hours=2160,
        baseline_data=FED_2022_BASELINE.copy(),
        treatment_deltas=FED_2022_TREATMENT_DELTA.copy(),
    )

    checks = {}
    for metric, truth in FED_GROUND_TRUTH.items():
        diff_vals = result.diff.get(metric, [])
        our_delta = max(diff_vals, key=abs) if diff_vals else 0.0
        error = abs(our_delta - truth) / abs(truth) if abs(truth) > 1e-10 else abs(our_delta)
        checks[metric] = {
            "our_delta": round(our_delta, 3),
            "truth_delta": truth,
            "error_pct": round(error * 100, 1),
            "passed": error <= TOLERANCE,
        }

    chain_ok = len(result.causal_edges) >= 3
    checks["chain_depth"] = {"depth": len(result.causal_edges), "passed": chain_ok}

    passed = sum(1 for c in checks.values() if c.get("passed", False))
    return {
        "scenario": "2022 Fed Rate Cycle",
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "overall_pass": passed >= 3,
    }


# ── Scenario 2: Texas Storm ───────────────────────────────────────────────────

TEXAS_BASELINE = {"NATGAS": 2.5, "MANUFACTURING": 100.0, "EMPLOYMENT": 95.0}
TEXAS_DELTAS = {"NATGAS": 20.0, "MANUFACTURING": 0.0, "EMPLOYMENT": 0.0}


async def validate_texas_storm() -> dict:
    engine = CounterfactualEngine()
    result = await engine.run_counterfactual(
        event_id="texas_storm_2021",
        horizon_hours=2160,
        baseline_data=TEXAS_BASELINE.copy(),
        treatment_deltas=TEXAS_DELTAS.copy(),
    )

    checks = {}

    # Natural gas should spike strongly positive
    natgas_diff = result.diff.get("NATGAS", [])
    if natgas_diff:
        peak = max(natgas_diff, key=abs)
        direction_ok = peak > 0
        checks["natgas_direction"] = {"peak_delta": round(peak, 2), "passed": direction_ok}

    # Manufacturing should go negative (propagated from NATGAS)
    mfg_diff = result.diff.get("MANUFACTURING", [])
    if mfg_diff:
        peak = min(mfg_diff)
        checks["manufacturing_direction"] = {"peak_delta": round(peak, 2), "passed": peak < 0}

    # Chain depth
    chain_ok = len(result.causal_edges) >= 3
    checks["chain_depth"] = {"depth": len(result.causal_edges), "passed": chain_ok}

    passed = sum(1 for c in checks.values() if c.get("passed", False))
    return {
        "scenario": "2021 Texas Winter Storm",
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "overall_pass": passed >= 2,
    }


# ── Scenario 3: COVID Supply Chain ───────────────────────────────────────────

COVID_BASELINE = {"AUTO_PRODUCTION": 100.0, "USED_CAR_PRICES": 100.0, "CPI": 100.0}
COVID_DELTAS = {"AUTO_PRODUCTION": -25.0, "USED_CAR_PRICES": 0.0, "CPI": 0.0}


async def validate_covid_supply() -> dict:
    engine = CounterfactualEngine()
    result = await engine.run_counterfactual(
        event_id="covid_supply_chain",
        horizon_hours=2160,
        baseline_data=COVID_BASELINE.copy(),
        treatment_deltas=COVID_DELTAS.copy(),
    )

    checks = {}

    # Auto production should be negative
    auto_diff = result.diff.get("AUTO_PRODUCTION", [])
    if auto_diff:
        peak = min(auto_diff)
        checks["auto_production_direction"] = {"peak_delta": round(peak, 2), "passed": peak < 0}

    # Chain depth
    chain_ok = len(result.causal_edges) >= 3
    checks["chain_depth"] = {"depth": len(result.causal_edges), "passed": chain_ok}

    # Cascade: at least 2 metrics show non-zero diff
    nonzero = sum(1 for v in result.diff.values() if v and max(abs(x) for x in v) > 0.01)
    checks["cascade"] = {"nonzero_metrics": nonzero, "passed": nonzero >= 2}

    passed = sum(1 for c in checks.values() if c.get("passed", False))
    return {
        "scenario": "COVID Supply Chain Shock",
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "overall_pass": passed >= 2,
    }


# ── Runner ────────────────────────────────────────────────────────────────────

async def main() -> bool:
    print("\nbutterfly-effect -- Phase 7 Validation Report")
    print("=" * 60)

    scenarios = [
        ("Fed 2022", validate_fed_2022),
        ("Texas Storm", validate_texas_storm),
        ("COVID Supply", validate_covid_supply),
    ]

    results = []
    for name, fn in scenarios:
        print(f"\nRunning: {name}...")
        r = await fn()
        results.append(r)

        print(f"  Scenario: {r['scenario']}")
        for check_name, check in r["checks"].items():
            status = "PASS" if check.get("passed") else "FAIL"
            detail = {k: v for k, v in check.items() if k != "passed"}
            print(f"    {status}  {check_name}: {detail}")
        print(f"  Result: {r['passed']}/{r['total']} checks -- {'PASS' if r['overall_pass'] else 'FAIL'}")

    scenarios_passed = sum(1 for r in results if r["overall_pass"])
    total_scenarios = len(results)

    print("\n" + "=" * 60)
    print(f"Overall: {scenarios_passed}/{total_scenarios} scenarios passed")
    gate = scenarios_passed >= 2
    print(f"\n{'PHASE 7 GATE PASSED' if gate else 'PHASE 7 GATE FAILED'}")
    print("=" * 60)

    return gate


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
