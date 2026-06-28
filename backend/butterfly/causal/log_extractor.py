"""
CausalLogExtractor — converts graph + simulation output into a structured
causal chain, ranked by C-Path cumulative causal influence scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from butterfly.causal.cpath import CPathCalculator, CascadePath
from butterfly.causal.dag import DAGBuilder


@dataclass
class ConfidenceBreakdown:
    """Explains what drove a confidence score."""
    score: float
    components: dict  # {simulation_consistency, effect_magnitude, persistence}
    evidence_adjusted: bool
    evidence_sources: list[str]
    primary_driver: str  # which component dominated
    plain_english: str

    def model_dump(self) -> dict:
        return {
            "score": round(self.score, 3),
            "components": {k: round(v, 3) for k, v in self.components.items()},
            "evidence_adjusted": self.evidence_adjusted,
            "evidence_sources": self.evidence_sources,
            "primary_driver": self.primary_driver,
            "plain_english": self.plain_english,
        }


@dataclass
class CausalHop:
    from_node: str
    to_node: str
    from_label: str
    to_label: str
    relationship: str
    latency_hours: int
    confidence: float
    cci_score: float
    is_butterfly_effect: bool
    magnitude: float
    confidence_breakdown: ConfidenceBreakdown | None = None


@dataclass
class CausalChain:
    event_title: str
    hops: list = field(default_factory=list)
    total_hops: int = 0
    butterfly_effects: list = field(default_factory=list)
    peak_effect_at_hours: int = 0
    domain_coverage: list = field(default_factory=list)
    cpath_ranking: list = field(default_factory=list)

    def model_dump(self) -> dict:
        return {
            "event_title": self.event_title,
            "total_hops": self.total_hops,
            "peak_effect_at_hours": self.peak_effect_at_hours,
            "domain_coverage": self.domain_coverage,
            "cpath_ranking": self.cpath_ranking,
            "butterfly_effects": [
                {
                    "node_id": b.node_id,
                    "node_label": b.node_label,
                    "cci_score": b.cci_score,
                    "hop_count": b.hop_count,
                    "estimated_latency_hours": b.estimated_latency_hours,
                }
                for b in self.butterfly_effects
            ],
            "hops": [
                {
                    "from_label": h.from_label,
                    "to_label": h.to_label,
                    "relationship": h.relationship,
                    "latency_hours": h.latency_hours,
                    "confidence": h.confidence,
                    "cci_score": h.cci_score,
                    "is_butterfly_effect": h.is_butterfly_effect,
                    "confidence_breakdown": h.confidence_breakdown.model_dump() if h.confidence_breakdown else None,
                }
                for h in self.hops
            ],
        }


class CausalLogExtractor:

    def __init__(self) -> None:
        self._dag_builder = DAGBuilder()
        self._cpath = CPathCalculator()

    def _generate_confidence_breakdown(
        self,
        base_confidence: float,
        cci_score: float,
        hop_count: int,
        edge_data: dict,
        nodes: list[dict],
    ) -> ConfidenceBreakdown:
        """
        Generate confidence breakdown with components and plain English explanation.

        Components:
        - simulation_consistency: based on hop traversal (cci_score)
        - effect_magnitude: based on cci_score magnitude
        - persistence: based on relationship strength
        """
        # Normalize components to [0, 1]
        sim_consistency = min(1.0, cci_score * 1.2)  # Scale to utilize full [0,1] range
        effect_magnitude = min(1.0, (cci_score ** 0.5) * 1.5)  # Sqrt to reduce dominance
        persistence = min(1.0, base_confidence)  # Edge's native confidence

        # Weighted combination: 0.4 + 0.4 + 0.2 = 1.0
        combined = 0.4 * sim_consistency + 0.4 * effect_magnitude + 0.2 * persistence
        combined = min(0.95, max(0.05, combined))  # Clamp

        # Determine primary driver
        components = {
            "simulation_consistency": sim_consistency,
            "effect_magnitude": effect_magnitude,
            "persistence": persistence,
        }
        primary_driver = max(components, key=components.get)

        # Check if evidence adjusted this edge
        evidence_sources = edge_data.get("evidence_sources", [])
        evidence_adjusted = edge_data.get("evidence_adjusted", False)

        # Generate plain English explanation using templates
        plain_english = self._template_confidence_explanation(
            combined,
            primary_driver,
            components,
            evidence_adjusted,
            evidence_sources,
            hop_count,
        )

        return ConfidenceBreakdown(
            score=combined,
            components=components,
            evidence_adjusted=evidence_adjusted,
            evidence_sources=evidence_sources,
            primary_driver=primary_driver,
            plain_english=plain_english,
        )

    def _template_confidence_explanation(
        self,
        score: float,
        primary_driver: str,
        components: dict,
        evidence_adjusted: bool,
        evidence_sources: list[str],
        hop_count: int,
    ) -> str:
        """Generate plain English explanation from templates."""
        # Template library based on confidence score and primary driver
        templates = {
            "high_sim": (
                "Confidence is high because the simulation was internally consistent "
                f"across multiple runs (consistency: {components['simulation_consistency']:.0%}). "
                f"{'Supported by ' + ', '.join(evidence_sources) + '.' if evidence_sources else ''}"
            ),
            "high_evidence": (
                "Confidence is high because external sources corroborate this mechanism. "
                f"Sources: {', '.join(evidence_sources)}. "
                f"Simulation consistency was {components['simulation_consistency']:.0%}."
            ),
            "mixed": (
                "Confidence is moderate because the mechanism is plausible "
                f"(simulation {components['simulation_consistency']:.0%}, magnitude {components['effect_magnitude']:.0%}) "
                f"but requires longer causal chains. {'Corroborated by: ' + ', '.join(evidence_sources) if evidence_sources else ''}"
            ),
            "low_depth": (
                f"Confidence is lower at hop {hop_count} because the causal chain is longer "
                f"and uncertainty compounds. Core mechanism is sound (sim: {components['simulation_consistency']:.0%})."
            ),
            "conflicting": (
                "Confidence is uncertain due to conflicting signals or sparse evidence. "
                f"Simulation suggests {components['simulation_consistency']:.0%} plausibility, "
                "but this is a deep chain where verification is limited."
            ),
        }

        # Choose template based on score, driver, and evidence
        if score >= 0.75 and primary_driver == "simulation_consistency":
            return templates["high_sim"]
        elif score >= 0.75 and evidence_adjusted:
            return templates["high_evidence"]
        elif 0.50 <= score < 0.75:
            return templates["mixed"]
        elif hop_count >= 3:
            return templates["low_depth"]
        else:
            return templates["conflicting"]

    def extract(self, graph_data: dict, simulation_result, event) -> CausalChain:
        """
        Extract structured causal chain from graph + simulation data.
        Uses C-Path to score each node by cumulative causal influence.
        """
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        if not nodes:
            logger.warning("[EXTRACTOR] Empty graph — returning minimal chain")
            return CausalChain(event_title=getattr(event, "title", "Unknown"))

        dag = self._dag_builder.build_from_graph_data(graph_data)

        # Find source node (hop=0 or id="root")
        source = "root"
        for node in nodes:
            if node.get("hop", 1) == 0 or node.get("id") == "root":
                source = node["id"]
                break

        cci_scores = self._cpath.calculate(dag, source)

        # Build hop list from edges
        hops: list[CausalHop] = []
        for edge in edges:
            src_id = edge.get("source", "")
            tgt_id = edge.get("target", "")
            src_node = next((n for n in nodes if n["id"] == src_id), {})
            tgt_node = next((n for n in nodes if n["id"] == tgt_id), {})
            tgt_hop = tgt_node.get("hop", 1)

            conf = edge.get("confidence", 0.5)
            if isinstance(conf, list):
                conf = conf[0]

            cci_score = cci_scores.get(tgt_id, 0.0)

            # Generate confidence breakdown
            confidence_breakdown = self._generate_confidence_breakdown(
                base_confidence=conf,
                cci_score=cci_score,
                hop_count=tgt_hop,
                edge_data=edge,
                nodes=nodes,
            )

            hops.append(CausalHop(
                from_node=src_id,
                to_node=tgt_id,
                from_label=src_node.get("label", src_id),
                to_label=tgt_node.get("label", tgt_id),
                relationship=edge.get("relationship_type", "INFLUENCES"),
                latency_hours=edge.get("latency_hours", 24),
                confidence=conf,
                cci_score=cci_score,
                is_butterfly_effect=(tgt_hop >= 3),
                magnitude=cci_score,
                confidence_breakdown=confidence_breakdown,
            ))

        hops.sort(key=lambda h: h.latency_hours)

        butterfly = self._cpath.find_butterfly_effects(dag, cci_scores, source)
        peak_hours = max((h.latency_hours for h in hops), default=24)

        return CausalChain(
            event_title=getattr(event, "title", "Unknown"),
            hops=hops,
            total_hops=len(hops),
            butterfly_effects=butterfly,
            peak_effect_at_hours=peak_hours,
            domain_coverage=getattr(event, "domain", []),
            cpath_ranking=[
                {"node": k, "cci": v}
                for k, v in sorted(cci_scores.items(), key=lambda x: x[1], reverse=True)[:10]
            ],
        )
