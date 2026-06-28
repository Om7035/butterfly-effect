"""
Uncertainty propagation through causal chains.

CORE PRINCIPLE: If hop 1 is 0.9 confident and hop 2 (conditional on hop 1) is 0.7,
then the probability of REACHING hop 2 is 0.9 * 0.7 = 0.63, NOT 0.7.

Most tools show each hop's confidence in isolation. This creates false certainty.
The honest approach: compound them.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class HopWithJointConfidence:
    """A hop with both individual and joint (accumulated) confidence."""
    order: int  # 1st, 2nd, 3rd, etc.
    description: str
    individual_confidence: float  # P(this hop | previous hops)
    joint_confidence: float  # P(reaching this hop from root)


class UncertaintyPropagator:
    """Propagates uncertainty through a causal chain."""

    @staticmethod
    def propagate_chain(hops_with_confidence: list[tuple[str, float]]) -> list[HopWithJointConfidence]:
        """
        Convert list of (description, confidence) into hops with joint confidence.

        Args:
            hops_with_confidence: List of (hop_description, individual_confidence)

        Returns:
            List of HopWithJointConfidence with both individual and joint confidence
        """
        result = []
        joint = 1.0  # Start at 100% (we know root occurred)

        for order, (description, individual_conf) in enumerate(hops_with_confidence, 1):
            joint = joint * individual_conf  # Compound: multiply confidences
            result.append(
                HopWithJointConfidence(
                    order=order,
                    description=description,
                    individual_confidence=individual_conf,
                    joint_confidence=joint,
                )
            )

        return result

    @staticmethod
    def format_chain_for_display(propagated_hops: list[HopWithJointConfidence]) -> str:
        """Format chain with both individual and joint confidence for display."""
        lines = []

        for hop in propagated_hops:
            order_label = ["1st", "2nd", "3rd", "4th", "5th"][hop.order - 1]
            lines.append(
                f"{order_label} order ({hop.description})\n"
                f"  Individual confidence: {hop.individual_confidence:.0%}\n"
                f"  Joint confidence (reaching this hop): {hop.joint_confidence:.0%}\n"
            )

        return "\n".join(lines)


def demonstrate_uncertainty_propagation():
    """Show how confidence should decay through a chain."""
    print("\n" + "=" * 80)
    print("UNCERTAINTY PROPAGATION EXAMPLE")
    print("=" * 80)

    # Example: Fed rate hike chain
    hops = [
        ("Bond yields rise", 0.90),
        ("Mortgage rates increase", 0.85),
        ("Housing demand falls", 0.75),
        ("Construction employment declines", 0.70),
    ]

    propagator = UncertaintyPropagator()
    propagated = propagator.propagate_chain(hops)

    print("\nFED RATE HIKE SCENARIO\n")
    print(propagator.format_chain_for_display(propagated))

    print("\nKEY INSIGHT:")
    print("-" * 80)
    print("""
The individual confidence of each hop might be high (0.7–0.9).
But the JOINT confidence of reaching the end of the chain is:

    0.90 * 0.85 * 0.75 * 0.70 = 0.40 (40%)

So if you see a 4-hop chain, you should expect:
  - 1st hop: ~90% likely
  - 2nd hop: ~77% likely (assuming 1st happened)
  - 3rd hop: ~57% likely (assuming 1-2 happened)
  - 4th hop: ~40% likely (assuming 1-3 happened)

This is why showing each hop's confidence separately is DISHONEST.
Users must understand: deep chains are inherently uncertain.

The fix: Always show BOTH individual and joint confidence.
    """)

    # More extreme example
    print("\n" + "=" * 80)
    print("EXTREME EXAMPLE: 5-HOP CHAIN")
    print("=" * 80)

    extreme_hops = [
        ("First consequence", 0.85),
        ("Second consequence", 0.80),
        ("Third consequence", 0.75),
        ("Fourth consequence", 0.70),
        ("Fifth consequence", 0.65),
    ]

    extreme_propagated = propagator.propagate_chain(extreme_hops)
    print("\n" + propagator.format_chain_for_display(extreme_propagated))

    final_confidence = extreme_propagated[-1].joint_confidence
    print(f"\nFINAL JOINT CONFIDENCE: {final_confidence:.1%}")
    print(f"Probability of reaching all 5 hops: {final_confidence:.0%}")
    print(f"\nConclusion: Showing 'hop 5: 65% confident' without context is MISLEADING.")
    print(f"Reality: There's only a ~13% chance of reaching hop 5 from the root.")


if __name__ == "__main__":
    demonstrate_uncertainty_propagation()
