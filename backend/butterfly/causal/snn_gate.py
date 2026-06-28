"""
SNN Verification Gate — Anti-Hallucination Layer.

Verifies LLM insights against FETCHED EVIDENCE TEXT (not the LLM-generated graph).
This is more honest: we check whether the insight's claims appear in real sources,
not whether they appear in a graph that was itself built from LLM output.

Confidence adjustment rules:
  - Key terms found in evidence corpus → confidence passes through
  - Partial match → confidence scaled by match ratio
  - No match in evidence → confidence capped at 0.3 (possible but unverified)
  - No evidence at all → confidence capped at 0.4 (LLM-only, flag it)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import networkx as nx
from loguru import logger


@dataclass
class VerifiedInsight:
    order: int
    hop: int
    text: str
    why: str
    confidence: float
    sources: list[str]
    snn_verified: bool
    snn_evidence_nodes: list[str] = field(default_factory=list)
    snn_max_cci: float = 0.0
    snn_rejection_reason: str = ""
    evidence_match_ratio: float = 0.0


class SNNVerificationGate:
    """
    Verifies insights against fetched evidence text.
    Falls back to graph-based check when no evidence available.
    """

    def __init__(self) -> None:
        self._evidence_corpus: str = ""

    def set_evidence(self, evidence: list) -> None:
        """Load fetched evidence into the corpus for verification."""
        texts = []
        for ev in evidence:
            t = getattr(ev, "title", "") or ""
            c = getattr(ev, "content", "") or ""
            texts.append((t + " " + c).lower())
        self._evidence_corpus = " ".join(texts)

    def verify_batch(
        self,
        insights: list[dict],
        dag: nx.DiGraph,
        cci_scores: dict[str, float],
        evidence: list | None = None,
    ) -> list[VerifiedInsight]:
        if evidence:
            self.set_evidence(evidence)

        verified = []
        for insight in insights:
            v = self._verify_one(insight, dag, cci_scores)
            verified.append(v)
            logger.debug(
                f"[SNN] order={v.order} evidence_match={v.evidence_match_ratio:.2f} "
                f"conf={v.confidence:.2f} verified={v.snn_verified}"
            )
        return verified

    def _verify_one(
        self,
        insight: dict,
        dag: nx.DiGraph,
        cci_scores: dict[str, float],
    ) -> VerifiedInsight:
        text = insight.get("text", "")
        why = insight.get("why", "")
        claimed_conf = float(insight.get("confidence", 0.5))
        order = int(insight.get("order", 2))
        hop = int(insight.get("hop", order))
        sources = list(insight.get("sources", []))

        key_terms = _extract_key_terms(text + " " + why)

        # Primary: check against fetched evidence text
        evidence_match = 0.0
        if self._evidence_corpus and key_terms:
            matches = sum(1 for t in key_terms if t in self._evidence_corpus)
            evidence_match = matches / len(key_terms)

        # Secondary: check against graph nodes (fallback)
        graph_match_nodes = []
        graph_max_cci = 0.0
        for node_id in dag.nodes():
            label = dag.nodes[node_id].get("label", node_id).lower()
            if any(t in label for t in key_terms):
                graph_match_nodes.append(node_id)
                graph_max_cci = max(graph_max_cci, cci_scores.get(node_id, 0.0))

        # Confidence adjustment
        if not self._evidence_corpus:
            # No evidence fetched — LLM-only, cap at 0.4
            final_conf = min(claimed_conf, 0.4)
            verified = len(graph_match_nodes) > 0
            reason = "No fetched evidence available — LLM-only claim, capped at 0.4"
        elif evidence_match >= 0.4:
            # Good evidence support
            final_conf = claimed_conf * (0.7 + 0.3 * evidence_match)
            final_conf = round(min(final_conf, 1.0), 3)
            verified = True
            reason = ""
        elif evidence_match > 0:
            # Partial evidence support
            final_conf = round(claimed_conf * evidence_match * 1.5, 3)
            final_conf = min(final_conf, 0.6)
            verified = True
            reason = f"Partial evidence match ({evidence_match:.0%}) — confidence scaled"
        else:
            # No evidence match — cap at 0.3
            final_conf = min(claimed_conf, 0.3)
            verified = False
            reason = f"No evidence match for terms: {key_terms[:4]} — possible hallucination"

        return VerifiedInsight(
            order=order, hop=hop, text=text, why=why,
            confidence=final_conf, sources=sources,
            snn_verified=verified,
            snn_evidence_nodes=graph_match_nodes,
            snn_max_cci=round(graph_max_cci, 3),
            snn_rejection_reason=reason,
            evidence_match_ratio=round(evidence_match, 3),
        )

    def to_frontend_format(self, verified: list[VerifiedInsight]) -> list[dict]:
        result = []
        for v in verified:
            d = {
                "order": v.order, "hop": v.hop,
                "text": v.text, "why": v.why,
                "confidence": round(v.confidence, 3),
                "sources": v.sources,
                "snn_verified": v.snn_verified,
                "snn_max_cci": v.snn_max_cci,
                "evidence_match": v.evidence_match_ratio,
            }
            if v.snn_rejection_reason:
                d["snn_warning"] = v.snn_rejection_reason
            result.append(d)
        return result


_STOPWORDS = {
    "this", "that", "with", "from", "have", "will", "been", "their",
    "which", "when", "where", "what", "order", "effect", "impact",
    "within", "after", "before", "during", "across", "through",
    "most", "more", "less", "very", "also", "into", "onto", "over",
    "under", "about", "above", "below", "between", "among", "around",
    "manifests", "cascades", "disruption", "analysis", "sector",
    "domain", "global", "local", "regional", "national", "international",
}


def _extract_key_terms(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    terms = [w for w in words if w not in _STOPWORDS]
    seen: set[str] = set()
    unique = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:12]
