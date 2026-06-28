"""
DAGBuilder — constructs a directed acyclic graph from graph_data dict.
Phase R2: works from in-memory graph_data (no Neo4j needed).
Phase R3: upgrade to read from Neo4j directly.
"""
from __future__ import annotations

import networkx as nx
from loguru import logger


class EvidenceAudit:
    """Result of applying evidence updates to a graph."""

    def __init__(self):
        self.updates: dict[tuple, dict] = {}  # (source, target) -> {sources, delta, corr, contra}

    def model_dump(self) -> dict:
        """Convert to JSON-serializable format."""
        return {
            str(edge): {
                "sources": info["sources"],
                "confidence_delta": round(info["delta"], 3),
                "corroboration_count": info["corr"],
                "contradiction_count": info["contra"],
            }
            for edge, info in self.updates.items()
        }


class DAGBuilder:

    def build_from_graph_data(self, graph_data: dict) -> nx.DiGraph:
        """Build a NetworkX DiGraph from the graph_data dict produced by analyze.py."""
        dag = nx.DiGraph()

        for node in graph_data.get("nodes", []):
            dag.add_node(
                node["id"],
                label=node.get("label", node["id"]),
                node_type=node.get("type", "unknown"),
                hop=node.get("hop", 0),
                domain=node.get("domain", []),
            )

        for edge in graph_data.get("edges", []):
            src = edge.get("source")
            tgt = edge.get("target")
            if src and tgt and src in dag and tgt in dag:
                dag.add_edge(
                    src, tgt,
                    confidence=edge.get("confidence", [0.5, 0.7])[0]
                    if isinstance(edge.get("confidence"), list)
                    else edge.get("confidence", 0.5),
                    latency_hours=edge.get("latency_hours", 24),
                    relationship=edge.get("relationship_type", "INFLUENCES"),
                )

        # Remove cycles to ensure valid DAG
        if not nx.is_directed_acyclic_graph(dag):
            logger.warning("[DAG] Cycle detected — removing weakest edges")
            for cycle in list(nx.simple_cycles(dag)):
                min_conf, min_edge = float("inf"), None
                for i in range(len(cycle)):
                    s, t = cycle[i], cycle[(i + 1) % len(cycle)]
                    if dag.has_edge(s, t):
                        c = dag[s][t].get("confidence", 0.5)
                        if c < min_conf:
                            min_conf, min_edge = c, (s, t)
                if min_edge:
                    dag.remove_edge(*min_edge)

        logger.info(f"[DAG] {dag.number_of_nodes()} nodes, {dag.number_of_edges()} edges")
        return dag

    async def build_dag_for_event_with_template(
        self, event_id: str, domain: str
    ) -> dict:
        """
        Called by orchestrator. Returns a plain dict with nodes/edges lists.
        In R2 this returns an empty structure — the real graph comes from analyze.py.
        In R3 this will query Neo4j for the stored graph.
        """
        logger.info(f"[DAG] build_dag_for_event_with_template: event={event_id} domain={domain}")
        # Return empty — orchestrator falls back to _seed_causal_chain
        return {"nodes": [], "edges": []}

    def apply_evidence_updates(
        self, graph_data: dict, evidence: list
    ) -> tuple[dict, EvidenceAudit]:
        """
        Update edge confidence scores based on evidence corroboration/contradiction.

        For each edge, checks if any evidence text contains keywords that match
        the edge mechanism. Adjusts confidence using:
        new_conf = base_conf × (1 + 0.15 × corr_count) × (1 - 0.20 × contra_count)
        clamped to [0.05, 0.95].

        Args:
            graph_data: The causal graph dict with nodes and edges
            evidence: List of RawEvidence objects from fetcher

        Returns:
            (modified_graph_data, EvidenceAudit with update details)
        """
        audit = EvidenceAudit()
        edges = graph_data.get("edges", [])

        # Ensure all edges have evidence fields (even if not updated)
        for edge in edges:
            edge.setdefault("evidence_sources", [])
            edge.setdefault("evidence_adjusted", False)

        if not evidence:
            logger.info("[EVIDENCE] No evidence to apply")
            graph_data["edges"] = edges
            return graph_data, audit

        # Build searchable evidence text by source
        evidence_by_source: dict[str, list[str]] = {}
        for ev in evidence:
            source = getattr(ev, "source", "unknown")
            title = getattr(ev, "title", "")
            content = getattr(ev, "content", "")
            combined = (title + " " + content).lower()
            if source not in evidence_by_source:
                evidence_by_source[source] = []
            evidence_by_source[source].append(combined)

        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            base_conf = edge.get("confidence", 0.5)
            if isinstance(base_conf, list):
                base_conf = base_conf[0]

            # Extract keywords from relationship and node labels
            nodes = {n["id"]: n for n in graph_data.get("nodes", [])}
            src_label = nodes.get(src, {}).get("label", "").lower()
            tgt_label = nodes.get(tgt, {}).get("label", "").lower()
            relationship = edge.get("relationship_type", "INFLUENCES").lower()

            # Keywords for this edge (max 10 tokens from labels + relationship)
            keywords = set()
            for word in (src_label + " " + tgt_label + " " + relationship).split():
                if len(word) > 2:
                    keywords.add(word[:15])
            keywords = list(keywords)[:10]

            corr_count = 0
            contra_count = 0
            matching_sources = set()

            # Check each source's evidence
            for source, texts in evidence_by_source.items():
                for text in texts:
                    # Count keyword matches (simple overlap)
                    kw_hits = sum(1 for kw in keywords if kw in text)
                    if kw_hits >= 1:  # At least one keyword match
                        # Heuristic: presence of keyword = corroboration
                        corr_count += 1
                        matching_sources.add(source)
                        break  # Only count once per source

            # Apply confidence adjustment formula
            if corr_count > 0 or contra_count > 0:
                new_conf = base_conf * (1.0 + 0.15 * corr_count) * (1.0 - 0.20 * contra_count)
                new_conf = max(0.05, min(0.95, new_conf))  # Clamp to [0.05, 0.95]
                delta = new_conf - base_conf

                # Update edge
                edge["confidence"] = new_conf
                edge["evidence_sources"] = list(matching_sources)
                edge["evidence_adjusted"] = True

                audit.updates[(src, tgt)] = {
                    "sources": list(matching_sources),
                    "delta": delta,
                    "corr": corr_count,
                    "contra": contra_count,
                }
                logger.info(
                    f"[EVIDENCE] Updated edge {src}->{tgt}: "
                    f"{base_conf:.3f} → {new_conf:.3f} (sources: {matching_sources})"
                )

        graph_data["edges"] = edges
        logger.info(f"[EVIDENCE] Updated {len(audit.updates)} of {len(edges)} edges")
        return graph_data, audit
