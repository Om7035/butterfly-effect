"""
Detect and handle cycles in causal graphs.

Real causality has feedback loops (Fed→recession→Fed cuts→recovery→inflation→Fed).
Pure DAGs reject these. This module detects cycles and allows them with damping
to prevent infinite loops.

Key insight: Damped cycles are more realistic than acyclic approximations.
"""

from dataclasses import dataclass
from typing import Optional
from collections import deque, defaultdict


@dataclass
class CycleInfo:
    """Information about a detected cycle."""
    nodes: list[str]  # Nodes in the cycle
    length: int  # Number of nodes
    mean_confidence: float  # Average edge confidence in cycle
    has_feedback: bool  # Is this a feedback loop (corrects initial effect)?


class CycleDetector:
    """Detects cycles in directed graphs using DFS."""

    def __init__(self):
        self.visited: set = set()
        self.rec_stack: set = set()
        self.cycles: list[CycleInfo] = []
        self.parent_map: dict[str, str] = {}

    def find_cycles(self, graph: dict) -> list[CycleInfo]:
        """
        Find all cycles in a graph using DFS.

        Args:
            graph: {"nodes": [...], "edges": [...]}

        Returns:
            List of CycleInfo for each cycle found
        """
        self.visited = set()
        self.rec_stack = set()
        self.cycles = []

        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        # Build adjacency list
        adjacency = defaultdict(list)
        edge_map = {}  # (source, target) -> edge for confidence lookup
        for edge in edges:
            src = edge.get("source")
            tgt = edge.get("target")
            adjacency[src].append(tgt)
            edge_map[(src, tgt)] = edge

        # DFS from each node
        for node in nodes:
            node_id = node.get("id")
            if node_id not in self.visited:
                self._dfs(node_id, adjacency, edge_map, [])

        return self.cycles

    def _dfs(self, node: str, adj: dict, edge_map: dict, path: list[str]):
        """DFS to find cycles."""
        self.visited.add(node)
        self.rec_stack.add(node)
        path.append(node)

        neighbors = adj.get(node, [])
        for neighbor in neighbors:
            if neighbor not in self.visited:
                self._dfs(neighbor, adj, edge_map, path)
            elif neighbor in self.rec_stack:
                # Found a cycle!
                cycle_start_idx = path.index(neighbor)
                cycle_nodes = path[cycle_start_idx:] + [neighbor]

                # Compute cycle statistics
                cycle_confidences = []
                for i in range(len(cycle_nodes) - 1):
                    src, tgt = cycle_nodes[i], cycle_nodes[i + 1]
                    edge = edge_map.get((src, tgt), {})
                    conf = edge.get("confidence", [0.5, 0.5])
                    if isinstance(conf, list):
                        conf = (conf[0] + conf[1]) / 2
                    cycle_confidences.append(conf)

                mean_conf = (
                    sum(cycle_confidences) / len(cycle_confidences)
                    if cycle_confidences
                    else 0.5
                )

                # Detect if this is a feedback loop
                # (e.g., does cycle include a corrective mechanism?)
                has_feedback = self._is_feedback_loop(cycle_nodes)

                self.cycles.append(
                    CycleInfo(
                        nodes=cycle_nodes[:-1],  # Don't repeat start node
                        length=len(cycle_nodes) - 1,
                        mean_confidence=mean_conf,
                        has_feedback=has_feedback,
                    )
                )

        path.pop()
        self.rec_stack.remove(node)

    def _is_feedback_loop(self, cycle_nodes: list[str]) -> bool:
        """
        Heuristic: Is this a feedback loop (corrects initial effect)?

        Examples of feedback:
        - Fed raises rates → Recession → Fed lowers rates (corrects)
        - Price rises → Demand falls → Price falls (corrects)

        Heuristic: Look for semantic opposites in the cycle.
        """
        # Simple heuristic: cycle length 3+ and contains "down/decline/fall/lower/cut"
        # and "up/rise/increase/higher/hike" = likely feedback
        keywords_negative = {"down", "decline", "fall", "lower", "cut", "reduce", "decrease"}
        keywords_positive = {"up", "rise", "increase", "higher", "hike", "grow", "surge"}

        text = " ".join(cycle_nodes).lower()
        has_negative = any(kw in text for kw in keywords_negative)
        has_positive = any(kw in text for kw in keywords_positive)

        return has_negative and has_positive


class CycleDampingStrategy:
    """
    Handles how to process cycles to avoid infinite loops.

    Strategies:
    1. Unroll: Allow N iterations then stop
    2. Damp: Reduce confidence with each iteration (asymptotic approach)
    3. Condense: Collapse cycle into a single stability node
    """

    @staticmethod
    def damp_cycle(
        cycle: CycleInfo,
        iterations: int = 3,
        damping_factor: float = 0.7,
    ) -> list[dict]:
        """
        Unroll a cycle with damping to prevent infinite loops.

        Example: Fed→recession→Fed cuts (cycle of length 3)
        Iteration 1: Full confidence
        Iteration 2: Confidence × 0.7
        Iteration 3: Confidence × 0.7² = 0.49

        Args:
            cycle: The cycle to unroll
            iterations: How many times to unroll
            damping_factor: Multiply confidence by this each iteration

        Returns:
            List of "virtual hops" representing unrolled cycle with damping
        """
        hops = []

        for iteration in range(1, iterations + 1):
            damp = damping_factor ** (iteration - 1)
            hop = {
                "nodes": cycle.nodes,
                "iteration": iteration,
                "confidence_damping": damp,
                "description": (
                    f"Cycle iteration {iteration} "
                    f"({cycle.length}-node loop, "
                    f"confidence × {damp:.1%})"
                ),
                "is_feedback": cycle.has_feedback,
            }
            hops.append(hop)

        return hops

    @staticmethod
    def detect_equilibrium(
        cycle: CycleInfo,
        initial_effect: float,
        damping_factor: float = 0.7,
        threshold: float = 0.01,
    ) -> dict:
        """
        Compute long-term equilibrium of a damped cycle.

        If Fed raises rates by 1%, what's the equilibrium after
        recession → Fed cuts → recovery → inflation?

        Using geometric series: equilibrium = initial × (1 / (1 - r))
        where r is the feedback strength.

        Args:
            cycle: The feedback cycle
            initial_effect: Initial magnitude (e.g., 1% rate hike)
            damping_factor: How much each iteration reduces (0.7 = 30% reduction)
            threshold: Stop when effect < threshold

        Returns:
            Equilibrium analysis
        """
        feedback_strength = 1 - damping_factor  # How much Fed "corrects"

        # Geometric series sum
        equilibrium = initial_effect * cycle.mean_confidence / (1 - feedback_strength + 0.001)

        return {
            "initial_effect": initial_effect,
            "feedback_strength": feedback_strength,
            "damping_factor": damping_factor,
            "equilibrium_effect": equilibrium,
            "ratio": equilibrium / initial_effect if initial_effect > 0 else 1.0,
            "interpretation": (
                f"Initial: {initial_effect:.2f}% -> "
                f"Long-term equilibrium: {equilibrium:.2f}% "
                f"(ratio: {equilibrium/initial_effect:.2f}x)"
            ),
        }


def demonstrate_cycle_detection():
    """Show cycle detection and feedback loop handling."""
    # Mock graph with a clear cycle
    mock_graph = {
        "nodes": [
            {"id": "fed_hike", "label": "Fed raises rates"},
            {"id": "recession", "label": "Recession begins"},
            {"id": "unemployment", "label": "Unemployment rises"},
            {"id": "fed_cut", "label": "Fed lowers rates"},
            {"id": "recovery", "label": "Recovery starts"},
            {"id": "inflation", "label": "Inflation rises"},
        ],
        "edges": [
            {"source": "fed_hike", "target": "recession", "confidence": [0.80, 0.95]},
            {"source": "recession", "target": "unemployment", "confidence": [0.75, 0.90]},
            {"source": "unemployment", "target": "fed_cut", "confidence": [0.70, 0.85]},
            {"source": "fed_cut", "target": "recovery", "confidence": [0.75, 0.90]},
            {"source": "recovery", "target": "inflation", "confidence": [0.65, 0.80]},
            {"source": "inflation", "target": "fed_hike", "confidence": [0.70, 0.85]},  # CYCLE!
        ],
    }

    print("\n" + "=" * 80)
    print("CYCLE DETECTION & FEEDBACK LOOPS EXAMPLE")
    print("=" * 80)

    # Detect cycles
    detector = CycleDetector()
    cycles = detector.find_cycles(mock_graph)

    print(f"\nCycles found: {len(cycles)}\n")

    for i, cycle in enumerate(cycles, 1):
        print(f"Cycle {i}:")
        print(f"  Nodes: {' -> '.join(cycle.nodes)} -> {cycle.nodes[0]}")
        print(f"  Length: {cycle.length} nodes")
        print(f"  Mean confidence: {cycle.mean_confidence:.0%}")
        print(f"  Is feedback loop: {cycle.has_feedback}")
        print()

        # Show damped unrolling
        strategy = CycleDampingStrategy()
        dampened_hops = strategy.damp_cycle(cycle, iterations=4, damping_factor=0.7)

        print(f"  Damped unrolling (4 iterations, 70% damping):")
        for hop in dampened_hops:
            print(
                f"    Iteration {hop['iteration']}: "
                f"confidence × {hop['confidence_damping']:.1%}"
            )

        # Show equilibrium
        equilibrium = strategy.detect_equilibrium(
            cycle, initial_effect=1.0, damping_factor=0.7
        )
        print(f"\n  Long-term equilibrium:")
        print(f"    {equilibrium['interpretation']}")

        print()

    print("=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    print("""
1. CYCLE DETECTION: Classic Fed cycle (raise rates -> recession -> lower rates)

2. DAMPING: Real feedback loops don't repeat forever. Each iteration weakens.
   - Iteration 1: Full effect (100%)
   - Iteration 2: Dampened (70%)
   - Iteration 3: Further dampened (49%)
   - Approaches equilibrium asymptotically

3. EQUILIBRIUM: Long-term effect is NOT infinite, but a specific value.
   - Initial: 1% Fed rate hike
   - Equilibrium: ~1.4% after all feedback loops settle

4. WHY THIS MATTERS:
   - DAGs assume causality flows one direction (unrealistic)
   - Feedback loops show reality: systems self-correct
   - Damping prevents mathematical infinity without losing realism

5. IMPLEMENTATION:
   - Detect cycles in causal graph
   - For each cycle found: unroll with damping
   - Combine with alternative chains to show possible equilibria
    """)


if __name__ == "__main__":
    demonstrate_cycle_detection()
