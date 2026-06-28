"""
Confidence intervals for causal chains.

Instead of point estimates ("hop confidence: 0.75"), show ranges:
"hop confidence: 0.62–0.88 (90% credible interval)"

This communicates uncertainty honestly and helps users understand
the range of plausible effects.
"""

from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class ConfidenceInterval:
    """A range with lower, point, and upper bounds."""
    lower: float  # 5th percentile
    point: float  # median / mean
    upper: float  # 95th percentile
    method: str  # how it was computed

    @property
    def width(self) -> float:
        """Width of the interval."""
        return self.upper - self.lower

    @property
    def margin_of_error(self) -> float:
        """Margin of error (half-width)."""
        return self.width / 2

    def __str__(self) -> str:
        """Human-readable format."""
        return f"{self.lower:.0%}–{self.upper:.0%} (point: {self.point:.0%})"


class IntervalEstimator:
    """Compute confidence intervals from model uncertainty."""

    @staticmethod
    def from_model_uncertainty(
        point_estimate: float,
        model_std: float = 0.10,
        confidence_level: float = 0.90,
    ) -> ConfidenceInterval:
        """
        Compute interval from model uncertainty (std dev of similar predictions).

        Args:
            point_estimate: The predicted value (0-1)
            model_std: Standard deviation from similar models (~10% typical)
            confidence_level: 0.90 for 90% interval (±1.645 SD), etc.

        Returns:
            ConfidenceInterval
        """
        # Z-score for confidence level
        z_scores = {0.68: 1.0, 0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_scores.get(confidence_level, 1.645)

        margin = z * model_std
        lower = max(0.0, point_estimate - margin)
        upper = min(1.0, point_estimate + margin)

        return ConfidenceInterval(
            lower=lower,
            point=point_estimate,
            upper=upper,
            method=f"model_std={model_std:.1%}, z={z}",
        )

    @staticmethod
    def from_evidence_base_rate(
        point_estimate: float,
        evidence_count: int,
        base_rate: float = 0.5,
        confidence_level: float = 0.90,
    ) -> ConfidenceInterval:
        """
        Bayesian interval: prior (base rate) + evidence.

        If we see N pieces of evidence about a hop (FRED data, GDELT mentions, etc),
        how certain are we? Start with weak prior, update with evidence.

        Args:
            point_estimate: The predicted value
            evidence_count: How many independent evidence sources support it
            base_rate: Prior belief (0.5 = completely uncertain)
            confidence_level: 90% or 95%, etc.

        Returns:
            ConfidenceInterval (narrower with more evidence)
        """
        # With more evidence, interval shrinks
        # 0 evidence: wide interval around base_rate
        # 5 evidence: tighter interval
        # 20 evidence: narrow interval
        shrinkage = 1.0 / (1.0 + evidence_count * 0.5)  # 0 to 1
        adjusted_point = base_rate + (point_estimate - base_rate) * (1 - shrinkage)

        # Standard deviation decreases with evidence
        base_std = 0.20  # With no evidence
        evidence_std = base_std * math.sqrt(shrinkage)

        z_scores = {0.68: 1.0, 0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
        z = z_scores.get(confidence_level, 1.645)
        margin = z * evidence_std

        lower = max(0.0, adjusted_point - margin)
        upper = min(1.0, adjusted_point + margin)

        return ConfidenceInterval(
            lower=lower,
            point=adjusted_point,
            upper=upper,
            method=f"bayesian, evidence={evidence_count}",
        )

    @staticmethod
    def from_backtest_calibration(
        point_estimate: float,
        confidence_bucket: str,  # "0.7-0.8", "0.8-0.9", etc.
        actual_accuracy: Optional[float] = None,
    ) -> ConfidenceInterval:
        """
        Use calibration data to adjust intervals.

        If our "0.8 confidence" predictions actually come true 65% of the time,
        we should adjust accordingly.

        Args:
            point_estimate: Stated confidence
            confidence_bucket: Which calibration bucket (e.g., "0.8-0.9")
            actual_accuracy: What we actually get (e.g., 0.65)

        Returns:
            Adjusted confidence interval
        """
        if actual_accuracy is None:
            # Fallback if no calibration data
            return IntervalEstimator.from_model_uncertainty(
                point_estimate, model_std=0.12
            )

        # Recalibration: stated vs. actual
        # If we said 0.8 but got 0.65, we're overconfident by 0.15
        adjustment = actual_accuracy - float(confidence_bucket.split("-")[0])

        adjusted_point = point_estimate + adjustment
        adjusted_point = max(0.0, min(1.0, adjusted_point))

        # Wider interval if we're badly miscalibrated
        miscalibration = abs(adjustment)
        penalty_std = 0.08 + miscalibration * 0.2  # Up to 0.28 std

        margin = 1.645 * penalty_std  # 90% CI
        lower = max(0.0, adjusted_point - margin)
        upper = min(1.0, adjusted_point + margin)

        return ConfidenceInterval(
            lower=lower,
            point=adjusted_point,
            upper=upper,
            method=f"calibration_adjusted, miscalibration={miscalibration:.1%}",
        )


def demonstrate_confidence_intervals():
    """Show how confidence intervals work."""
    print("\n" + "=" * 80)
    print("CONFIDENCE INTERVALS DEMONSTRATION")
    print("=" * 80)

    # Example 1: Point estimate with model uncertainty
    print("\nExample 1: Model Uncertainty")
    print("-" * 80)
    print("Question: If Fed raises rates, will mortgage rates increase within 48h?")
    print("Point estimate: 0.82 (82% confident)")
    print()

    estimator = IntervalEstimator()
    interval_1 = estimator.from_model_uncertainty(0.82, model_std=0.08)
    print(f"90% Confidence Interval: {interval_1}")
    print(f"Interpretation: 'We think 82%, but plausibly 69–95%'")
    print()

    # Example 2: With evidence
    print("Example 2: Evidence-Based Adjustment")
    print("-" * 80)
    print("Same prediction, but now we have 5 sources of evidence:")
    print("  - FRED mortgage rate data (trending up)")
    print("  - Wall Street Journal report (mortgage rate rise)")
    print("  - Economic analyst forecasts (higher rates expected)")
    print("  - Historical precedent (happened in 2022)")
    print("  - Market futures (pricing in higher rates)")
    print()

    interval_2 = estimator.from_evidence_base_rate(0.82, evidence_count=5)
    print(f"90% Confidence Interval (with 5 evidence sources): {interval_2}")
    print(f"Narrower because evidence reduces uncertainty.")
    print()

    # Example 3: Calibration-adjusted
    print("Example 3: Calibration Adjustment")
    print("-" * 80)
    print("Backtest data shows: when we predict '0.8–0.9 confidence',")
    print("we're actually right only 62% of the time (miscalibration: -20%)")
    print()

    interval_3 = estimator.from_backtest_calibration(
        point_estimate=0.82,
        confidence_bucket="0.8-0.9",
        actual_accuracy=0.62,
    )
    print(f"Calibration-adjusted interval: {interval_3}")
    print(f"Why wider: Our 0.8 confidence is actually ~0.60 accurate.")
    print(f"Conservative: Show wider range to account for miscalibration.")
    print()

    # Example 4: Compare across different hops
    print("Example 4: Interval Widening Across Hops")
    print("-" * 80)

    hops = [
        ("Hop 1: Bond yields rise", 0.90, 5),
        ("Hop 2: Mortgage rates increase", 0.85, 4),
        ("Hop 3: Housing demand falls", 0.70, 2),
        ("Hop 4: Construction employment declines", 0.55, 1),
    ]

    print("As chain gets longer, uncertainty accumulates:\n")
    for label, point, evidence in hops:
        interval = estimator.from_evidence_base_rate(point, evidence)
        width = interval.width
        bar = "=" * int(width * 30)
        print(f"{label:45} {interval}  [{bar}]")

    print()
    print("=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    print("""
1. POINT ESTIMATES ARE LIES: "85% confident" sounds precise but is fundamentally
   uncertain. Show ranges instead.

2. MORE EVIDENCE SHRINKS INTERVALS: 5 sources of evidence gives tighter intervals
   than 1 source. This is honest uncertainty quantification.

3. CALIBRATION MATTERS: If your model says 90% but achieves 60%, admit it by
   widening intervals. This forces honesty.

4. LONGER CHAINS = WIDER INTERVALS: Each hop adds uncertainty. A 4-hop chain
   should have a MUCH wider interval than a 1-hop chain.

5. DISPLAY IN UI:
   Instead of: "Confidence: 0.85"
   Show:       "Confidence: 0.72–0.94 (point: 0.82)"

6. FRONTEND IMPLICATIONS:
   - Wider bars for uncertain hops
   - Smaller font/dimmer color for high-uncertainty predictions
   - Tooltip showing why interval is wide or narrow
    """)


if __name__ == "__main__":
    demonstrate_confidence_intervals()
