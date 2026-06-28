"""
Run calibration analysis on all historical backtests.

Compares tool's stated confidence scores against actual accuracy.
"""

import asyncio
from typing import Optional
from loguru import logger

from butterfly.backtesting.cases import BACKTEST_CASES, get_case
from butterfly.backtesting.runner import BacktestRunner
from butterfly.backtesting.scorer import ChainScorer
from butterfly.backtesting.calibration import CalibrationAnalyzer, CalibrationAnalysis


class CalibrationBacktestRunner:
    """Runs backtests and collects calibration data."""

    def __init__(self):
        self.backtest_runner = BacktestRunner()
        self.calibration_analyzer = CalibrationAnalyzer()
        self.results: list[dict] = []

    async def run_all_cases(self) -> CalibrationAnalysis:
        """
        Run all backtest cases and analyze calibration.

        For each case:
        1. Run the analysis
        2. Score against known outcomes
        3. Extract confidence from predicted chain
        4. Record whether predictions were correct
        5. Build calibration buckets

        Returns complete calibration analysis.
        """
        logger.info("Starting calibration backtest run on all cases...")

        # In production, this would call the full analysis pipeline.
        # For now, use mock_score_case which returns realistic synthetic results.
        for case_id in [case.id for case in BACKTEST_CASES]:
            logger.info(f"[CALIBRATION] Running case: {case_id}")

            try:
                result = await self._run_case_with_calibration(case_id)
                self.results.append(result)
            except Exception as e:
                logger.error(f"[CALIBRATION] Case {case_id} failed: {e}")

        # Compute final analysis
        analysis = self.calibration_analyzer.analyze()
        return analysis

    async def _run_case_with_calibration(self, case_id: str) -> dict:
        """Run a single case and extract calibration data."""
        case = get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        # Get mock score (in production: call full analysis pipeline)
        score_result = self.backtest_runner.mock_score_case(case_id)

        if score_result.get("status") != "success":
            raise RuntimeError(f"Case {case_id} analysis failed")

        predicted_hops = score_result.get("predicted_chain", [])
        known_outcomes = score_result.get("known_outcomes", [])

        # Score the chain
        scorer = ChainScorer()
        score = scorer.score_chain(
            predicted_hops,
            known_outcomes
        )

        # Extract calibration data from each hop comparison
        # For each predicted hop, we have a similarity score (confidence-like)
        hop_calibrations = []
        for comparison in score.hop_comparisons:
            # Map similarity score to confidence (0-1 range)
            confidence = comparison.similarity_score

            # Determine if correct (matched or partial counts as correct)
            correct = comparison.match_type in ("matched", "partial")

            # Record prediction for calibration analysis
            self.calibration_analyzer.add_prediction(confidence, correct)

            hop_calibrations.append({
                "hop": comparison.predicted_hop_number,
                "predicted": comparison.predicted_description[:60],
                "actual": comparison.actual_description[:60],
                "confidence": round(confidence, 2),
                "correct": correct,
                "match_type": comparison.match_type,
            })

        result = {
            "case_id": case_id,
            "event": case.event,
            "total_hops": len(predicted_hops),
            "matched_hops": score.matched_hops,
            "partial_hops": score.partial_hops,
            "missed_hops": score.missed_hops,
            "unknown_hops": score.unknown_hops,
            "accuracy_score": round(score.accuracy_score, 3),
            "hop_calibrations": hop_calibrations,
        }

        logger.info(
            f"[CALIBRATION] {case_id}: "
            f"{score.matched_hops + score.partial_hops}/{score.predicted_chain_length} matched/partial, "
            f"accuracy={score.accuracy_score:.1%}"
        )

        return result

    def print_report(self, analysis: CalibrationAnalysis):
        """Print human-readable calibration report."""
        print("\n" + "=" * 80)
        print("CALIBRATION ANALYSIS REPORT")
        print("=" * 80)

        print(f"\nGOVERNANCE METRICS:")
        print(f"  Total predictions analyzed: {analysis.total_predictions}")
        print(f"  Overall accuracy: {analysis.overall_accuracy:.1%}")
        if analysis.brier_score is not None:
            print(f"  Brier score: {analysis.brier_score:.3f} (lower is better, 0=perfect)")
        if analysis.mean_calibration_error is not None:
            print(f"  Mean calibration error: +/- {analysis.mean_calibration_error:.1%}")

        if analysis.buckets and any(b.count > 0 for b in analysis.buckets):
            print(f"\nCALIBRATION BUCKETS:")
            print(f"  Range          Stated    Actual    Error     Count")
            print(f"  " + "-" * 50)
            for bucket in analysis.buckets:
                if bucket.count > 0:
                    actual_str = f"{bucket.actual_accuracy:.0%}" if bucket.actual_accuracy is not None else "N/A"
                    error_str = f"+/- {bucket.calibration_error:.0%}" if bucket.calibration_error is not None else "N/A"
                    print(
                        f"  {bucket.confidence_range:>8} "
                        f"  {bucket.stated_confidence:>6.0%}    "
                        f"{actual_str:>6}    "
                        f"{error_str:>8}    "
                        f"n={bucket.count}"
                    )

        print("\nINTERPRETATION:")
        if analysis.mean_calibration_error is None:
            print("  (No data)")
        elif analysis.mean_calibration_error <= 0.05:
            print(
                "  ✓ EXCELLENT: Stated confidence matches actual accuracy "
                "within 5%. Tool's confidence scores are trustworthy."
            )
        elif analysis.mean_calibration_error <= 0.10:
            print(
                "  ~ GOOD: Confidence is mostly accurate, but with some "
                "systematic bias. Consider adding calibration metadata."
            )
        elif analysis.mean_calibration_error <= 0.20:
            print(
                "  ! WARNING: Systematic miscalibration detected. Tool tends "
                "to be [overconfident/underconfident]. Confidence scores "
                "should be adjusted or caveated."
            )
        else:
            print(
                "  X POOR: Confidence scores are meaningless. Tool is badly "
                "miscalibrated. Overhaul confidence calculation."
            )

        print("\nBRIER SCORE CONTEXT:")
        if analysis.brier_score is not None:
            if analysis.brier_score < 0.20:
                rating = "EXCELLENT"
            elif analysis.brier_score < 0.30:
                rating = "GOOD"
            elif analysis.brier_score < 0.50:
                rating = "FAIR"
            else:
                rating = "POOR"
            print(
                f"  Brier score = {analysis.brier_score:.3f} ({rating})\n"
                f"  Measures mean squared error of (predicted probability, actual).\n"
                f"  For reference: random guessing at 0.5 confidence = 0.25 Brier score.\n"
                f"  This tool's Brier score is {rating.lower()} for probabilistic accuracy."
            )

        print("\n" + "=" * 80)


async def run_calibration_analysis():
    """Run full calibration analysis on all cases."""
    runner = CalibrationBacktestRunner()
    analysis = await runner.run_all_cases()
    runner.print_report(analysis)
    return analysis, runner.results


if __name__ == "__main__":
    analysis, results = asyncio.run(run_calibration_analysis())
    print("\nDetailed results per case:")
    for result in results:
        print(f"\n{result['case_id']}:")
        print(f"  Accuracy: {result['accuracy_score']:.1%}")
        print(f"  Hops matched: {result['matched_hops']}/{result['total_hops']}")
