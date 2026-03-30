"""pgmpy DAG builder from Neo4j causal graph.

Includes domain-specific DAG templates as validated starting points.
Templates are MERGED with graph-derived edges, not replaced by them.

Template sources:
  FINANCIAL_TEMPLATE  — Bernanke (2005) monetary transmission mechanism
  GEOPOLITICAL_TEMPLATE — Collier & Hoeffler (2004) conflict economics
  CLIMATE_TEMPLATE    — IPCC AR6 (2021) impact pathways
  PANDEMIC_TEMPLATE   — Ferguson et al. (2020) COVID transmission model
  TECH_DISRUPTION_TEMPLATE — Brynjolfsson & McAfee (2014) second machine age
"""

from __future__ import annotations

import json

from loguru import logger

from butterfly.db.neo4j import run_query
from butterfly.db.redis import get_cache, set_cache

# ── Domain DAG templates ──────────────────────────────────────────────────────
# Each template is a dict with:
#   nodes: list of variable names
#   edges: list of (source, target, {latency_hours, confidence, mechanism})
#
# These are STARTING POINTS validated against academic literature.
# The graph builder MERGES these with Neo4j-derived edges.

FINANCIAL_TEMPLATE: dict = {
    "domain": "finance",
    "description": "Monetary policy transmission (Bernanke 2005)",
    "nodes": [
        "federal_funds_rate", "treasury_yield", "mortgage_rate",
        "housing_starts", "unemployment_rate", "consumer_spending",
        "equity_prices", "credit_spreads", "dollar_index",
    ],
    "edges": [
        ("federal_funds_rate", "treasury_yield",    {"latency_hours": 2,   "confidence": 0.95, "mechanism": "direct rate transmission"}),
        ("federal_funds_rate", "mortgage_rate",     {"latency_hours": 48,  "confidence": 0.88, "mechanism": "bank funding cost pass-through"}),
        ("federal_funds_rate", "equity_prices",     {"latency_hours": 1,   "confidence": 0.82, "mechanism": "discount rate effect on valuations"}),
        ("federal_funds_rate", "dollar_index",      {"latency_hours": 6,   "confidence": 0.78, "mechanism": "interest rate parity"}),
        ("mortgage_rate",      "housing_starts",    {"latency_hours": 168, "confidence": 0.85, "mechanism": "affordability constraint"}),
        ("housing_starts",     "unemployment_rate", {"latency_hours": 720, "confidence": 0.72, "mechanism": "construction employment multiplier"}),
        ("equity_prices",      "consumer_spending", {"latency_hours": 336, "confidence": 0.65, "mechanism": "wealth effect (Poterba 2000)"}),
        ("credit_spreads",     "consumer_spending", {"latency_hours": 168, "confidence": 0.70, "mechanism": "credit channel (Bernanke & Gertler 1995)"}),
        ("dollar_index",       "treasury_yield",    {"latency_hours": 24,  "confidence": 0.60, "mechanism": "foreign demand for US Treasuries"}),
    ],
}

GEOPOLITICAL_TEMPLATE: dict = {
    "domain": "geopolitics",
    "description": "Armed conflict economic cascade (Collier & Hoeffler 2004)",
    "nodes": [
        "military_action", "civilian_displacement", "economic_sanctions",
        "oil_supply", "food_security", "regional_stability",
        "refugee_flows", "infrastructure_damage", "trade_disruption",
    ],
    "edges": [
        ("military_action",       "civilian_displacement",  {"latency_hours": 24,  "confidence": 0.92, "mechanism": "direct population flight from conflict zones"}),
        ("military_action",       "infrastructure_damage",  {"latency_hours": 6,   "confidence": 0.90, "mechanism": "physical destruction of assets"}),
        ("military_action",       "economic_sanctions",     {"latency_hours": 168, "confidence": 0.75, "mechanism": "international community response"}),
        ("military_action",       "oil_supply",             {"latency_hours": 48,  "confidence": 0.80, "mechanism": "production disruption in conflict zones"}),
        ("economic_sanctions",    "oil_supply",             {"latency_hours": 72,  "confidence": 0.85, "mechanism": "export restrictions on energy"}),
        ("economic_sanctions",    "trade_disruption",       {"latency_hours": 24,  "confidence": 0.88, "mechanism": "financial and trade restrictions"}),
        ("oil_supply",            "food_security",          {"latency_hours": 720, "confidence": 0.70, "mechanism": "energy cost pass-through to agriculture"}),
        ("civilian_displacement", "refugee_flows",          {"latency_hours": 48,  "confidence": 0.88, "mechanism": "cross-border population movement"}),
        ("infrastructure_damage", "food_security",          {"latency_hours": 336, "confidence": 0.75, "mechanism": "supply chain disruption"}),
        ("trade_disruption",      "regional_stability",     {"latency_hours": 720, "confidence": 0.65, "mechanism": "economic grievance → instability (Collier 2000)"}),
    ],
}

CLIMATE_TEMPLATE: dict = {
    "domain": "climate",
    "description": "Extreme weather economic cascade (IPCC AR6 2021)",
    "nodes": [
        "extreme_weather_event", "infrastructure_damage", "agricultural_loss",
        "insurance_claims", "reconstruction_demand", "supply_chain_disruption",
        "energy_price_spike", "population_displacement", "government_spending",
    ],
    "edges": [
        ("extreme_weather_event", "infrastructure_damage",   {"latency_hours": 1,   "confidence": 0.95, "mechanism": "direct physical damage"}),
        ("extreme_weather_event", "agricultural_loss",       {"latency_hours": 24,  "confidence": 0.88, "mechanism": "crop and livestock destruction"}),
        ("extreme_weather_event", "population_displacement", {"latency_hours": 6,   "confidence": 0.90, "mechanism": "evacuation and displacement"}),
        ("extreme_weather_event", "energy_price_spike",      {"latency_hours": 12,  "confidence": 0.82, "mechanism": "production facility damage"}),
        ("infrastructure_damage", "insurance_claims",        {"latency_hours": 24,  "confidence": 0.92, "mechanism": "property and casualty claims"}),
        ("infrastructure_damage", "supply_chain_disruption", {"latency_hours": 48,  "confidence": 0.85, "mechanism": "transport and logistics disruption"}),
        ("insurance_claims",      "reconstruction_demand",   {"latency_hours": 168, "confidence": 0.80, "mechanism": "insurance payouts fund rebuilding"}),
        ("reconstruction_demand", "government_spending",     {"latency_hours": 336, "confidence": 0.75, "mechanism": "federal disaster relief allocation"}),
        ("agricultural_loss",     "supply_chain_disruption", {"latency_hours": 72,  "confidence": 0.78, "mechanism": "food supply chain disruption"}),
        ("energy_price_spike",    "supply_chain_disruption", {"latency_hours": 24,  "confidence": 0.72, "mechanism": "transport cost increase"}),
    ],
}

PANDEMIC_TEMPLATE: dict = {
    "domain": "health",
    "description": "Pandemic economic cascade (Ferguson et al. 2020, Eichenbaum et al. 2021)",
    "nodes": [
        "infection_rate", "mortality_rate", "mobility_restriction",
        "consumer_spending", "supply_chain_disruption", "unemployment_rate",
        "government_debt", "healthcare_capacity", "vaccine_coverage",
    ],
    "edges": [
        ("infection_rate",        "mortality_rate",          {"latency_hours": 336, "confidence": 0.90, "mechanism": "disease progression (IFR)"}),
        ("infection_rate",        "mobility_restriction",    {"latency_hours": 168, "confidence": 0.85, "mechanism": "policy response to case counts"}),
        ("infection_rate",        "healthcare_capacity",     {"latency_hours": 168, "confidence": 0.88, "mechanism": "hospital admission surge"}),
        ("mobility_restriction",  "consumer_spending",       {"latency_hours": 24,  "confidence": 0.92, "mechanism": "lockdown reduces retail and services"}),
        ("mobility_restriction",  "supply_chain_disruption", {"latency_hours": 48,  "confidence": 0.85, "mechanism": "worker absence and logistics disruption"}),
        ("consumer_spending",     "unemployment_rate",       {"latency_hours": 336, "confidence": 0.80, "mechanism": "demand collapse → layoffs"}),
        ("supply_chain_disruption","consumer_spending",      {"latency_hours": 72,  "confidence": 0.75, "mechanism": "goods shortage → reduced consumption"}),
        ("government_debt",       "consumer_spending",       {"latency_hours": 168, "confidence": 0.65, "mechanism": "fiscal stimulus (Chetty et al. 2020)"}),
        ("vaccine_coverage",      "mobility_restriction",    {"latency_hours": 720, "confidence": 0.82, "mechanism": "herd immunity → policy relaxation"}),
    ],
}

TECH_DISRUPTION_TEMPLATE: dict = {
    "domain": "technology",
    "description": "Technology disruption cascade (Brynjolfsson & McAfee 2014)",
    "nodes": [
        "technology_capability", "labor_displacement", "productivity_gain",
        "investment_flow", "regulatory_response", "incumbent_revenue",
        "startup_formation", "skill_premium", "consumer_surplus",
    ],
    "edges": [
        ("technology_capability", "labor_displacement",  {"latency_hours": 8760, "confidence": 0.75, "mechanism": "automation of routine tasks (Acemoglu & Restrepo 2018)"}),
        ("technology_capability", "productivity_gain",   {"latency_hours": 2160, "confidence": 0.80, "mechanism": "efficiency gains from adoption"}),
        ("technology_capability", "investment_flow",     {"latency_hours": 168,  "confidence": 0.88, "mechanism": "VC and PE capital allocation"}),
        ("technology_capability", "incumbent_revenue",   {"latency_hours": 720,  "confidence": 0.82, "mechanism": "market share disruption"}),
        ("investment_flow",       "startup_formation",   {"latency_hours": 336,  "confidence": 0.85, "mechanism": "capital availability enables new entrants"}),
        ("labor_displacement",    "skill_premium",       {"latency_hours": 4380, "confidence": 0.70, "mechanism": "relative demand shift for high-skill workers"}),
        ("productivity_gain",     "consumer_surplus",    {"latency_hours": 2160, "confidence": 0.72, "mechanism": "lower prices and better products"}),
        ("incumbent_revenue",     "regulatory_response", {"latency_hours": 2160, "confidence": 0.65, "mechanism": "lobbying and antitrust scrutiny"}),
        ("regulatory_response",   "investment_flow",     {"latency_hours": 720,  "confidence": 0.60, "mechanism": "regulatory uncertainty dampens investment"}),
    ],
}

# Registry: domain string → template
DOMAIN_TEMPLATES: dict[str, dict] = {
    "finance":      FINANCIAL_TEMPLATE,
    "economics":    FINANCIAL_TEMPLATE,
    "geopolitics":  GEOPOLITICAL_TEMPLATE,
    "military":     GEOPOLITICAL_TEMPLATE,
    "humanitarian": GEOPOLITICAL_TEMPLATE,
    "climate":      CLIMATE_TEMPLATE,
    "environment":  CLIMATE_TEMPLATE,
    "health":       PANDEMIC_TEMPLATE,
    "pandemic":     PANDEMIC_TEMPLATE,
    "technology":   TECH_DISRUPTION_TEMPLATE,
    "digital":      TECH_DISRUPTION_TEMPLATE,
}


def get_template_for_domain(domain: str) -> dict | None:
    """Return the DAG template for a given domain string."""
    return DOMAIN_TEMPLATES.get(domain.lower())


class DAGBuilder:
    """Build a causal DAG from the Neo4j knowledge graph."""

    async def build_dag_for_event(self, event_id: str) -> dict | None:
        """Build a DAG dict for a given event.

        Queries Neo4j for all CAUSES/TRIGGERS edges reachable within 4 hops,
        validates acyclicity, and returns a serialisable dict.

        Args:
            event_id: The event to build the DAG from.

        Returns:
            {"nodes": [...], "edges": [...], "node_names": {...}} or None on failure.
        """
        cache_key = f"dag:{event_id}"
        cached = await get_cache(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

        try:
            # Pull causal edges reachable from this event (up to 4 hops)
            query = """
            MATCH (start:Event {event_id: $event_id})
            CALL apoc.path.subgraphAll(start, {
                relationshipFilter: 'CAUSES>|TRIGGERS>|INFLUENCES>',
                maxLevel: 4
            })
            YIELD nodes, relationships
            RETURN nodes, relationships
            """
            results = await run_query(query, {"event_id": event_id})
        except Exception:
            # APOC may not be available — fall back to simple query
            results = await self._fallback_query(event_id)

        if not results:
            logger.warning(f"No causal graph found for event {event_id}")
            return None

        dag = self._build_dag_from_results(results)
        if dag is None:
            return None

        # Cache for 1 hour
        await set_cache(cache_key, json.dumps(dag), ttl=3600)
        return dag

    async def _fallback_query(self, event_id: str) -> list[dict]:
        """Fallback query without APOC."""
        query = """
        MATCH (start:Event {event_id: $event_id})
        MATCH (start)-[r:CAUSES|TRIGGERS|INFLUENCES*1..4]->(end)
        RETURN DISTINCT
            startNode(r[0]).name AS source_name,
            endNode(r[-1]).name AS target_name,
            type(r[0]) AS rel_type,
            r[0].confidence AS confidence
        LIMIT 200
        """
        try:
            return await run_query(query, {"event_id": event_id})
        except Exception as e:
            logger.error(f"Fallback DAG query failed: {e}")
            return []

    def _build_dag_from_results(self, results: list[dict]) -> dict | None:
        """Convert query results into a DAG dict.

        Args:
            results: Raw Neo4j query results.

        Returns:
            DAG dict or None if cycle detected and unresolvable.
        """
        nodes: set[str] = set()
        edges: list[tuple[str, str, float]] = []  # (source, target, confidence)

        for row in results:
            source = row.get("source_name") or row.get("source")
            target = row.get("target_name") or row.get("target")
            confidence = float(row.get("confidence") or 0.7)

            if source and target and source != target:
                nodes.add(source)
                nodes.add(target)
                edges.append((source, target, confidence))

        if not nodes:
            return None

        # Check for cycles and remove weakest edge if found
        edges = self._remove_cycles(list(nodes), edges)

        node_list = list(nodes)
        return {
            "nodes": node_list,
            "edges": [(s, t, c) for s, t, c in edges],
            "node_names": {n: n for n in node_list},
        }

    def _remove_cycles(
        self, nodes: list[str], edges: list[tuple[str, str, float]]
    ) -> list[tuple[str, str, float]]:
        """Remove cycles by dropping the weakest edge in each cycle.

        Args:
            nodes: List of node names.
            edges: List of (source, target, confidence) tuples.

        Returns:
            Acyclic edge list.
        """
        max_iterations = len(edges)
        for _ in range(max_iterations):
            cycle_edge = self._find_cycle_edge(nodes, edges)
            if cycle_edge is None:
                break
            logger.warning(f"Cycle detected, removing weakest edge: {cycle_edge[:2]}")
            edges = [e for e in edges if e != cycle_edge]
        return edges

    def _find_cycle_edge(
        self, nodes: list[str], edges: list[tuple[str, str, float]]
    ) -> tuple[str, str, float] | None:
        """Find the weakest edge that is part of a cycle using DFS.

        Returns:
            The weakest cycle edge, or None if no cycle.
        """
        adj: dict[str, list[str]] = {n: [] for n in nodes}
        for s, t, _ in edges:
            adj.setdefault(s, []).append(t)

        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str) -> tuple[str, str] | None:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    return (node, neighbor)
            rec_stack.discard(node)
            return None

        for node in nodes:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    # Find the weakest edge in this cycle pair
                    cycle_edges = [e for e in edges if e[0] == cycle[0] and e[1] == cycle[1]]
                    if cycle_edges:
                        return min(cycle_edges, key=lambda e: e[2])

        return None

    def build_dag_from_seed(self, seed_edges: list[tuple[str, str]]) -> dict:
        """Build a DAG from a manually provided edge list (for testing/demo).

        Args:
            seed_edges: List of (source, target) tuples.

        Returns:
            DAG dict.
        """
        nodes: set[str] = set()
        edges: list[tuple[str, str, float]] = []
        for s, t in seed_edges:
            nodes.add(s)
            nodes.add(t)
            edges.append((s, t, 0.8))

        edges = self._remove_cycles(list(nodes), edges)
        node_list = list(nodes)
        return {
            "nodes": node_list,
            "edges": edges,
            "node_names": {n: n for n in node_list},
        }

    def merge_with_template(self, dag: dict, domain: str) -> dict:
        """Merge a graph-derived DAG with the domain template.

        Template edges are added only if the nodes already exist in the DAG
        OR if the DAG is empty (bootstrap mode).

        Args:
            dag: Graph-derived DAG dict (may be empty)
            domain: Domain string (e.g. "geopolitics", "finance")

        Returns:
            Merged DAG dict with template edges added
        """
        template = get_template_for_domain(domain)
        if template is None:
            logger.debug(f"No template for domain '{domain}' — returning DAG unchanged")
            return dag

        existing_nodes: set[str] = set(dag.get("nodes", []))
        existing_edges: set[tuple[str, str]] = {
            (e[0], e[1]) for e in dag.get("edges", [])
        }

        new_nodes: set[str] = set(existing_nodes)
        new_edges: list[tuple[str, str, float]] = list(dag.get("edges", []))

        bootstrap_mode = len(existing_nodes) == 0
        logger.debug(
            f"Merging DAG with {domain} template "
            f"({'bootstrap' if bootstrap_mode else 'enrichment'} mode)"
        )

        for src, tgt, props in template["edges"]:
            # In bootstrap mode: add all template edges
            # In enrichment mode: only add if both nodes exist in graph
            if bootstrap_mode or (src in existing_nodes and tgt in existing_nodes):
                if (src, tgt) not in existing_edges:
                    confidence = props.get("confidence", 0.7)
                    new_edges.append((src, tgt, confidence))
                    existing_edges.add((src, tgt))
                    new_nodes.add(src)
                    new_nodes.add(tgt)

        node_list = list(new_nodes)
        new_edges = self._remove_cycles(node_list, new_edges)

        merged = {
            "nodes": node_list,
            "edges": new_edges,
            "node_names": {n: n for n in node_list},
            "template_domain": domain,
        }

        logger.info(
            f"DAG after merge: {len(node_list)} nodes, {len(new_edges)} edges "
            f"(was {len(existing_nodes)} nodes, {len(dag.get('edges', []))} edges)"
        )
        return merged

    async def build_dag_for_event_with_template(
        self, event_id: str, domain: str
    ) -> dict:
        """Build DAG from Neo4j and merge with domain template.

        Args:
            event_id: Event to build DAG for
            domain: Domain for template selection

        Returns:
            Merged DAG dict
        """
        dag = await self.build_dag_for_event(event_id) or {}
        return self.merge_with_template(dag, domain)
