"""
Calibration analysis for confidence scores.

Determines whether stated confidence values match actual accuracy.
Gold-standard metric for probabilistic forecasting (Tetlock, Brier scores).

If the tool says a prediction has 0.7 confidence, does it come true ~70% of the time?
If so, confidence is well-calibrated. If not, the tool is overconfident or underconfident.
"""

from dataclasses import dataclass, field
from typing import Optional
import json
import math


@dataclass
class CalibrationBucket:
    """Predictions grouped by stated confidence range."""
    confidence_range: str  # "0.0-0.2", "0.2-0.4", etc.
    stated_confidence: float  # Midpoint or average
    count: int  # Number of predictions
    correct: int  # Number that came true
    actual_accuracy: Optional[float] = None  # correct / count
    calibration_error: Optional[float] = None  # abs(stated - actual)

    def compute_stats(self):
        """Compute accuracy and calibration error."""
        if self.count > 0:
            self.actual_accuracy = self.correct / self.count
            self.calibration_error = abs(self.stated_confidence - self.actual_accuracy)
        else:
            self.actual_accuracy = None
            self.calibration_error = None


@dataclass
class CalibrationAnalysis:
    """Complete calibration report for all predictions."""
    total_predictions: int
    total_correct: int
    overall_accuracy: float  # Brier score context
    buckets: list[CalibrationBucket] = field(default_factory=list)
    mean_calibration_error: Optional[float] = None  # Mean absolute calibration error
    brier_score: Optional[float] = None  # Mean squared error of (predicted, actual)

    def compute_aggregate_stats(self):
        """Compute mean calibration error and Brier score."""
        if not self.buckets:
            return

        # Compute mean absolute calibration error
        errors = [b.calibration_error for b in self.buckets if b.calibration_error is not None]
        if errors:
            self.mean_calibration_error = sum(errors) / len(errors)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON output."""
        return {
            "total_predictions": self.total_predictions,
            "total_correct": self.total_correct,
            "overall_accuracy": round(self.overall_accuracy, 3),
            "mean_calibration_error": round(self.mean_calibration_error, 3) if self.mean_calibration_error else None,
            "brier_score": round(self.brier_score, 3) if self.brier_score else None,
            "buckets": [
                {
                    "range": b.confidence_range,
                    "stated_confidence": round(b.stated_confidence, 2),
                    "count": b.count,
                    "correct": b.correct,
                    "actual_accuracy": round(b.actual_accuracy, 3) if b.actual_accuracy else None,
                    "calibration_error": round(b.calibration_error, 3) if b.calibration_error else None,
                }
                for b in self.buckets
            ],
        }


class CalibrationAnalyzer:
    """Analyzes confidence calibration across predictions."""

    # Standard 5-bucket calibration scheme (Tetlock)
    CONFIDENCE_BUCKETS = [
        (0.0, 0.2, "0.0-0.2"),
        (0.2, 0.4, "0.2-0.4"),
        (0.4, 0.6, "0.4-0.6"),
        (0.6, 0.8, "0.6-0.8"),
        (0.8, 1.0, "0.8-1.0"),
    ]

    def __init__(self):
        self.predictions: list[tuple[float, bool]] = []  # (confidence, correct)

    def add_prediction(self, confidence: float, correct: bool):
        """Record a single prediction with its confidence and outcome."""
        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
        self.predictions.append((confidence, correct))

    def analyze(self) -> CalibrationAnalysis:
        """Compute calibration statistics."""
        if not self.predictions:
            return CalibrationAnalysis(
                total_predictions=0,
                total_correct=0,
                overall_accuracy=0.0,
            )

        total_preds = len(self.predictions)
        total_correct = sum(1 for _, correct in self.predictions if correct)
        overall_accuracy = total_correct / total_preds if total_preds > 0 else 0.0

        # Bucket predictions
        buckets: list[CalibrationBucket] = []
        for low, high, label in self.CONFIDENCE_BUCKETS:
            bucket_preds = [
                correct for conf, correct in self.predictions
                if low <= conf < high or (high == 1.0 and conf <= high)
            ]

            bucket = CalibrationBucket(
                confidence_range=label,
                stated_confidence=(low + high) / 2,
                count=len(bucket_preds),
                correct=sum(1 for correct in bucket_preds if correct),
            )
            bucket.compute_stats()
            buckets.append(bucket)

        # Compute aggregate statistics
        analysis = CalibrationAnalysis(
            total_predictions=total_preds,
            total_correct=total_correct,
            overall_accuracy=overall_accuracy,
            buckets=buckets,
        )
        analysis.compute_aggregate_stats()

        # Compute Brier score: mean squared error of (predicted_prob, actual_outcome)
        brier_score_sum = sum(
            (confidence - (1.0 if correct else 0.0)) ** 2
            for confidence, correct in self.predictions
        )
        analysis.brier_score = brier_score_sum / total_preds if total_preds > 0 else 0.0

        return analysis

    def generate_ascii_plot(self, analysis: CalibrationAnalysis) -> str:
        """Generate ASCII calibration plot (x = stated, y = actual accuracy)."""
        if not analysis.buckets or not any(b.actual_accuracy is not None for b in analysis.buckets):
            return "No data for calibration plot"

        lines = [
            "+-- Calibration Plot (diagonal = well-calibrated) -------+",
            "| x = stated confidence -> y = actual accuracy           |",
            "|                                                        |",
        ]

        # Create a 50-char wide plot
        plot_width = 50
        plot_height = 10

        # Find min/max for scaling
        max_confidence = 1.0
        max_accuracy = max(
            (b.actual_accuracy for b in analysis.buckets if b.actual_accuracy is not None),
            default=1.0,
        )
        max_axis = max(max_confidence, max_accuracy, 1.0)

        # Build plot grid
        grid = [["." for _ in range(plot_width)] for _ in range(plot_height)]

        # Draw diagonal (perfect calibration)
        for row in range(plot_height):
            col = round(row * plot_width / plot_height)
            if 0 <= col < plot_width:
                grid[row][col] = "-"

        # Plot actual bucket points
        for bucket in analysis.buckets:
            if bucket.actual_accuracy is None or bucket.count == 0:
                continue

            x = int((bucket.stated_confidence / max_axis) * (plot_width - 1))
            y = plot_height - 1 - int((bucket.actual_accuracy / max_axis) * (plot_height - 1))

            x = max(0, min(plot_width - 1, x))
            y = max(0, min(plot_height - 1, y))

            # Mark with bucket count
            marker = str(min(9, bucket.count))
            grid[y][x] = marker

        # Add plot to lines
        for row in grid:
            lines.append("| " + "".join(row) + " |")

        lines.extend([
            "| 0                                             1        |",
            "| (stated confidence) -> (actual accuracy)              |",
            "+-------------------------------------------------------+",
        ])

        return "\n".join(lines)


def demonstrate_calibration():
    """Example: show calibration analysis."""
    analyzer = CalibrationAnalyzer()

    # Example predictions (confidence, outcome_correct)
    test_cases = [
        # Well-calibrated 0.7 range: 3 correct out of 4 = 75%
        (0.7, True), (0.7, True), (0.7, False), (0.7, True),
        # Overconfident 0.9 range: 3 correct out of 4 = 75% (should be ~90%)
        (0.9, True), (0.9, False), (0.9, False), (0.9, True),
        # Under-confident 0.3 range: 1 correct out of 2 = 50% (should be ~30%)
        (0.3, True), (0.3, False),
        # Perfect 0.5 range: 2 out of 4 = 50%
        (0.5, True), (0.5, False), (0.5, True), (0.5, False),
    ]

    for confidence, correct in test_cases:
        analyzer.add_prediction(confidence, correct)

    analysis = analyzer.analyze()

    print("\n" + "=" * 60)
    print("CALIBRATION ANALYSIS EXAMPLE")
    print("=" * 60)
    print(f"\nTotal predictions: {analysis.total_predictions}")
    print(f"Overall accuracy: {analysis.overall_accuracy:.1%}")
    print(f"Brier score: {analysis.brier_score:.3f} (lower is better)")
    print(f"Mean calibration error: +/- {analysis.mean_calibration_error:.1%}")

    print("\n" + analyzer.generate_ascii_plot(analysis))

    print("\nBucket breakdown:")
    print("-" * 70)
    for bucket in analysis.buckets:
        if bucket.count > 0:
            print(
                f"{bucket.confidence_range:>8}  |  "
                f"stated={bucket.stated_confidence:.1%}  "
                f"actual={bucket.actual_accuracy:.1%}  "
                f"error=+/-{bucket.calibration_error:.1%}  "
                f"n={bucket.count}"
            )

    return analysis


if __name__ == "__main__":
    demonstrate_calibration()
