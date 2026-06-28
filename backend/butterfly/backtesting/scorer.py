"""Score predicted chains against known outcomes."""

from dataclasses import dataclass
from typing import Literal

from loguru import logger


@dataclass
class HopComparison:
    """Comparison between predicted and actual hop."""
    predicted_hop_number: int
    predicted_description: str
    actual_description: str
    match_type: Literal["matched", "partial", "missed", "unknown"]
    similarity_score: float  # 0-1, higher is better


@dataclass
class BacktestScore:
    """Overall score for a backtest case."""
    case_id: str
    predicted_chain_length: int
    actual_chain_length: int
    matched_hops: int
    partial_hops: int
    missed_hops: int
    unknown_hops: int
    accuracy_score: float  # Overall percentage
    hop_comparisons: list[HopComparison]


class ChainScorer:
    """Scores predicted chains against known outcomes."""

    def __init__(self):
        self.keyword_weights = {
            "exact_match": 1.0,
            "partial_match": 0.7,
            "keyword_match": 0.4,
        }

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity based on keyword overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    def _classify_hop_match(
        self, predicted: str, actual: str
    ) -> tuple[Literal["matched", "partial", "missed"], float]:
        """Classify how well a predicted hop matches an actual outcome."""
        similarity = self._text_similarity(predicted, actual)

        # Exact match: very high similarity or key keywords
        if similarity > 0.6:
            return "matched", min(1.0, similarity + 0.1)

        # Partial match: some overlap but not exact
        if similarity > 0.3:
            return "partial", similarity

        # Missed: no meaningful overlap
        return "missed", similarity

    def score_chain(
        self,
        predicted_hops: list[str],
        known_outcomes: list[dict],
    ) -> BacktestScore:
        """
        Score a predicted chain against known outcomes.

        Args:
            case_id: ID of the case
            predicted_hops: List of predicted hop descriptions
            known_outcomes: List of {"hop": int, "description": str, ...}

        Returns:
            BacktestScore with detailed comparison
        """
        comparisons: list[HopComparison] = []
        matched = partial = missed = unknown = 0

        # Track which known outcomes have been matched
        matched_outcome_indices = set()

        # For each predicted hop, find best matching outcome
        for pred_idx, predicted in enumerate(predicted_hops, start=1):
            best_match: tuple[int, Literal["matched", "partial", "missed"], float] | None = None
            best_score = 0.0

            # Compare against all known outcomes
            for outcome_idx, outcome in enumerate(known_outcomes):
                if outcome_idx in matched_outcome_indices:
                    continue  # Already matched this outcome

                actual = outcome.get("description", "")
                match_type, score = self._classify_hop_match(predicted, actual)

                if score > best_score:
                    best_score = score
                    best_match = (outcome_idx, match_type, score)

            # Record comparison
            if best_match:
                outcome_idx, match_type, score = best_match
                matched_outcome_indices.add(outcome_idx)
                comparisons.append(
                    HopComparison(
                        predicted_hop_number=pred_idx,
                        predicted_description=predicted,
                        actual_description=known_outcomes[outcome_idx]["description"],
                        match_type=match_type,
                        similarity_score=score,
                    )
                )
                if match_type == "matched":
                    matched += 1
                elif match_type == "partial":
                    partial += 1
                else:
                    missed += 1
            else:
                # No known outcome to compare (prediction beyond known data)
                comparisons.append(
                    HopComparison(
                        predicted_hop_number=pred_idx,
                        predicted_description=predicted,
                        actual_description="(no known outcome)",
                        match_type="unknown",
                        similarity_score=0.0,
                    )
                )
                unknown += 1

        # Calculate overall accuracy score
        # Matched counts as 100%, partial as 50%, missed/unknown as 0%
        if comparisons:
            total_score = (
                matched * 1.0 + partial * 0.5
            ) / len(comparisons)
        else:
            total_score = 0.0

        return BacktestScore(
            case_id="",  # Set by caller
            predicted_chain_length=len(predicted_hops),
            actual_chain_length=len(known_outcomes),
            matched_hops=matched,
            partial_hops=partial,
            missed_hops=missed,
            unknown_hops=unknown,
            accuracy_score=total_score,
            hop_comparisons=comparisons,
        )

    def format_result(self, score: BacktestScore) -> dict:
        """Convert BacktestScore to JSON-serializable format."""
        return {
            "case_id": score.case_id,
            "predicted_chain_length": score.predicted_chain_length,
            "actual_chain_length": score.actual_chain_length,
            "matched_hops": score.matched_hops,
            "partial_hops": score.partial_hops,
            "missed_hops": score.missed_hops,
            "unknown_hops": score.unknown_hops,
            "accuracy_score": round(score.accuracy_score * 100, 1),
            "summary": (
                f"On {score.matched_hops + score.partial_hops} of "
                f"{score.predicted_chain_length} predicted hops, "
                f"the tool identified correct or partially-correct mechanisms. "
                f"Accuracy: {round(score.accuracy_score * 100, 0):.0f}%."
            ),
            "hop_comparisons": [
                {
                    "predicted_hop": c.predicted_hop_number,
                    "predicted_description": c.predicted_description,
                    "actual_description": c.actual_description,
                    "match_type": c.match_type,
                    "similarity": round(c.similarity_score, 2),
                }
                for c in score.hop_comparisons
            ],
        }
