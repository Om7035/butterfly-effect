"""
Alternative causal chains — showing multiple plausible futures.

Instead of a single predicted chain (false certainty), show:
- Primary chain (highest probability)
- Alternative 1 (second-highest, "less likely but consistent")
- Alternative 2 (third-highest, "low probability but possible")

This is honest forecasting. Real causality is multimodal.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CausalChain:
    """A single causal chain with probability."""
    rank: int  # 1 = primary, 2 = alternative, etc.
    hops: list[dict]  # List of hop nodes with confidence
    cumulative_probability: float  # Product of edge confidences
    description: str  # "Primary chain", "Alternative (30% likely)", etc.

    def compute_joint_confidence(self) -> float:
        """
        Compute actual joint probability of the entire chain.

        If each hop has confidence c_i, then probability of reaching
        the end is c_1 * c_2 * c_3 * ... (compound uncertainty).

        This is the HONEST way to show chain confidence.
        """
        if not self.hops:
            return 0.0

        joint = 1.0
        for hop in self.hops:
            confidence = hop.get("confidence", 0.5)
            joint *= confidence

        return max(0.0, min(1.0, joint))


class AlternativeChainsBuilder:
    """Builds multiple plausible causal chains from a single DAG."""

    @staticmethod
    def extract_top_k_chains(
        graph: dict,
        k: int = 3,
        max_chain_length: int = 5,
    ) -> list[CausalChain]:
        """
        Extract top-k causal chains from a graph (by path probability).

        Args:
            graph: {"nodes": [...], "edges": [...]}
            k: Number of chains to return
            max_chain_length: Maximum hops per chain

        Returns:
            List of top-k CausalChains, ranked by probability.
        """
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        if not nodes or not edges:
            return []

        # Find root node (hop=0)
        root = next((n for n in nodes if n.get("hop") == 0), None)
        if not root:
            return []

        # Build adjacency: node_id -> [(target_id, edge_confidence)]
        adjacency = {}
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            conf = edge.get("confidence", [0.5, 0.7])
            # Use mid-point or high-end of confidence range
            edge_conf = (conf[0] + conf[1]) / 2 if isinstance(conf, list) else conf

            if src not in adjacency:
                adjacency[src] = []
            adjacency[src].append((tgt, edge_conf))

        # DFS to find all paths from root
        all_paths = []

        def dfs(node_id: str, path: list[dict], prob: float):
            """DFS to find all paths (up to max_chain_length)."""
            if len(path) >= max_chain_length:
                all_paths.append((path[:], prob))
                return

            if node_id in adjacency:
                for next_id, edge_conf in adjacency[node_id]:
                    next_node = next((n for n in nodes if n["id"] == next_id), None)
                    if next_node:
                        new_prob = prob * edge_conf
                        new_path = path + [next_node]
                        dfs(next_id, new_path, new_prob)

            # Also consider stopping here (path terminus)
            if path:
                all_paths.append((path[:], prob))

        dfs(root["id"], [root], 1.0)

        # Sort paths by probability (descending)
        all_paths.sort(key=lambda x: x[1], reverse=True)

        # Build CausalChain objects for top-k
        chains = []
        for rank, (path, prob) in enumerate(all_paths[:k], start=1):
            if rank == 1:
                description = "Primary chain (highest probability)"
            elif rank == 2:
                description = f"Alternative ({prob:.0%} likely) - less probable but consistent with evidence"
            else:
                description = f"Alternative ({prob:.0%} likely) - low probability but possible"

            chains.append(
                CausalChain(
                    rank=rank,
                    hops=path,
                    cumulative_probability=prob,
                    description=description,
                )
            )

        return chains


def demonstrate_alternative_chains():
    """Example: extract alternative chains from a graph."""
    # Mock graph
    mock_graph = {
        "nodes": [
            {"id": "root", "hop": 0, "label": "Fed raises rates", "confidence": 0.95},
            {"id": "n1", "hop": 1, "label": "Bond yields rise", "confidence": 0.90},
            {"id": "n2", "hop": 1, "label": "Financial conditions tighten", "confidence": 0.85},
            {"id": "n3", "hop": 2, "label": "Mortgage rates increase", "confidence": 0.80},
            {"id": "n4", "hop": 2, "label": "Corporate borrowing costs rise", "confidence": 0.75},
            {"id": "n5", "hop": 3, "label": "Housing demand falls", "confidence": 0.70},
            {"id": "n6", "hop": 3, "label": "Business investment declines", "confidence": 0.65},
        ],
        "edges": [
            {"source": "root", "target": "n1", "confidence": [0.85, 0.95]},
            {"source": "root", "target": "n2", "confidence": [0.75, 0.90]},
            {"source": "n1", "target": "n3", "confidence": [0.75, 0.85]},
            {"source": "n1", "target": "n4", "confidence": [0.70, 0.80]},
            {"source": "n2", "target": "n4", "confidence": [0.65, 0.75]},
            {"source": "n3", "target": "n5", "confidence": [0.60, 0.80]},
            {"source": "n4", "target": "n6", "confidence": [0.55, 0.75]},
        ],
    }

    chains = AlternativeChainsBuilder.extract_top_k_chains(mock_graph, k=3)

    print("\n" + "=" * 80)
    print("ALTERNATIVE CHAINS EXAMPLE")
    print("=" * 80)

    for chain in chains:
        print(f"\n{chain.description}")
        print(f"Joint confidence: {chain.compute_joint_confidence():.1%}")
        print("  Path:")
        for i, hop in enumerate(chain.hops, 1):
            confidence = hop.get("confidence", 0.5)
            print(f"    {i}. {hop['label']} (individual confidence: {confidence:.0%})")
        print(f"  Compound probability of entire chain: {chain.cumulative_probability:.1%}")

    print("\n" + "=" * 80)
    print("INTERPRETATION:")
    print("=" * 80)
    print("""
The primary chain shows the most likely causal sequence.
The alternatives show what else could plausibly happen if the
primary chain breaks down at certain points.

Key insight: Notice how the compound probability of each chain
(product of hop confidences) decays as you go deeper. This is
HONEST representation of uncertainty.

Instead of showing each hop's confidence in isolation (which creates
false certainty), compound them so users understand that:
  - Reaching hop 1 at 90% means reaching hop 2 is at 90% × 85% = 76.5%
  - By hop 3, you're at 90% × 85% × 70% = 53.6%

This is why longer chains should have lower stated confidence.
    """)


if __name__ == "__main__":
    demonstrate_alternative_chains()
