// =============================================================================
// butterfly-effect — Universal Causal Knowledge Graph Schema
// Neo4j 5.x Community Edition
// Migration-safe: all statements use IF NOT EXISTS
// =============================================================================
// DESIGN PHILOSOPHY:
//   Nodes  = things that exist (events, actors, systems, resources, metrics...)
//   Edges  = causal or structural relationships between them
//   Every edge carries: confidence, latency, mechanism — no naked relationships
// =============================================================================

// ─────────────────────────────────────────────────────────────────────────────
// NODE CONSTRAINTS (uniqueness + existence)
// ─────────────────────────────────────────────────────────────────────────────

// Event — something that happened at a point in time
CREATE CONSTRAINT event_id IF NOT EXISTS
  FOR (n:Event) REQUIRE n.event_id IS UNIQUE;

// Actor — any agent that acts: nation-states, companies, people, algorithms
CREATE CONSTRAINT actor_id IF NOT EXISTS
  FOR (n:Actor) REQUIRE n.actor_id IS UNIQUE;

// System — structural systems that things flow through or depend on
//   e.g. "global semiconductor supply chain", "SWIFT payment network", "US power grid"
CREATE CONSTRAINT system_id IF NOT EXISTS
  FOR (n:System) REQUIRE n.system_id IS UNIQUE;

// Resource — things that flow: oil, food, capital, data, people, electricity
CREATE CONSTRAINT resource_id IF NOT EXISTS
  FOR (n:Resource) REQUIRE n.resource_id IS UNIQUE;

// Metric — quantifiable measures: prices, rates, counts, temperatures, indices
CREATE CONSTRAINT metric_id IF NOT EXISTS
  FOR (n:Metric) REQUIRE n.metric_id IS UNIQUE;

// Policy — rules, decisions, laws, sanctions, tariffs, treaties, mandates
CREATE CONSTRAINT policy_id IF NOT EXISTS
  FOR (n:Policy) REQUIRE n.policy_id IS UNIQUE;

// Location — geographic nodes: countries, regions, cities, chokepoints
CREATE CONSTRAINT location_id IF NOT EXISTS
  FOR (n:Location) REQUIRE n.location_id IS UNIQUE;

// Belief — narrative/sentiment nodes: public opinion, market sentiment, propaganda
CREATE CONSTRAINT belief_id IF NOT EXISTS
  FOR (n:Belief) REQUIRE n.belief_id IS UNIQUE;

// Legacy node labels (kept for backward compatibility)
CREATE CONSTRAINT entity_id IF NOT EXISTS
  FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE;

CREATE CONSTRAINT causal_edge_id IF NOT EXISTS
  FOR (n:CausalEdge) REQUIRE n.edge_id IS UNIQUE;

// ─────────────────────────────────────────────────────────────────────────────
// INDEXES (query performance)
// ─────────────────────────────────────────────────────────────────────────────

// Time-based queries (most common: "what happened around X date?")
CREATE INDEX event_occurred_at IF NOT EXISTS
  FOR (n:Event) ON (n.occurred_at);

CREATE INDEX event_domain IF NOT EXISTS
  FOR (n:Event) ON (n.domain);

// Actor lookups
CREATE INDEX actor_name IF NOT EXISTS
  FOR (n:Actor) ON (n.name);

CREATE INDEX actor_type IF NOT EXISTS
  FOR (n:Actor) ON (n.type);

// Location lookups
CREATE INDEX location_name IF NOT EXISTS
  FOR (n:Location) ON (n.name);

CREATE INDEX location_country_code IF NOT EXISTS
  FOR (n:Location) ON (n.country_code);

// Metric lookups (for time-series correlation)
CREATE INDEX metric_name IF NOT EXISTS
  FOR (n:Metric) ON (n.name);

CREATE INDEX metric_series_id IF NOT EXISTS
  FOR (n:Metric) ON (n.series_id);

// Resource lookups
CREATE INDEX resource_name IF NOT EXISTS
  FOR (n:Resource) ON (n.name);

CREATE INDEX resource_type IF NOT EXISTS
  FOR (n:Resource) ON (n.type);

// System lookups
CREATE INDEX system_domain IF NOT EXISTS
  FOR (n:System) ON (n.domain);

// ─────────────────────────────────────────────────────────────────────────────
// RELATIONSHIP TYPE DOCUMENTATION
// (Neo4j doesn't support inline comments on relationships, so documented here)
// ─────────────────────────────────────────────────────────────────────────────
//
// CAUSES {confidence, latency_hours, mechanism, validated}
//   Semantics: A directly produces B as a necessary consequence.
//   Use when: there is a clear mechanistic pathway from A to B.
//   Example: Fed rate hike CAUSES treasury yield increase
//   Required: confidence (0-1), latency_hours (int), mechanism (str)
//
// TRIGGERS {confidence, latency_hours, threshold, conditions}
//   Semantics: A activates B when a threshold is crossed.
//   Use when: B only happens if A exceeds some level (not always).
//   Example: Conflict intensity TRIGGERS refugee displacement (above threshold)
//   Required: confidence, latency_hours, threshold (description of trigger condition)
//
// INFLUENCES {direction, strength, latency_hours, mechanism}
//   Semantics: A changes the probability or magnitude of B.
//   direction: "increases" | "decreases" | "destabilizes" | "stabilizes"
//   Use when: A affects B but doesn't deterministically cause it.
//   Example: Oil price INFLUENCES inflation (direction: increases)
//   Required: direction, strength (0-1), latency_hours
//
// DISRUPTS {severity, recovery_days, domain, mechanism}
//   Semantics: A damages or interrupts the normal functioning of B.
//   Use when: A breaks something that was working.
//   Example: Hurricane DISRUPTS supply chain (severity: 0.8, recovery_days: 90)
//   Required: severity (0-1), recovery_days (int), domain (str)
//
// DEPENDS_ON {criticality, substitutability, dependency_type}
//   Semantics: A requires B to function normally.
//   criticality: how badly A fails without B (0-1)
//   substitutability: how easily B can be replaced (0-1, 0=irreplaceable)
//   Use when: modeling structural vulnerabilities.
//   Example: European energy DEPENDS_ON Russian gas (criticality: 0.7, substitutability: 0.3)
//   Required: criticality, substitutability
//
// ESCALATES_TO {probability, conditions, timeline_days}
//   Semantics: A can evolve into B under certain conditions.
//   Use when: modeling conflict escalation, crisis progression.
//   Example: Border skirmish ESCALATES_TO full conflict (probability: 0.3)
//   Required: probability (0-1), conditions (str)
//
// DISPLACES {volume, destination, mechanism}
//   Semantics: A forces B to move from one place/state to another.
//   Use when: modeling refugee flows, capital flight, supply rerouting.
//   Example: Conflict DISPLACES population (volume: "2M people", destination: "Jordan")
//   Required: volume (str), destination (str)
//
// RETALIATES {actor, mechanism, probability, timeline_days}
//   Semantics: A responds to B with a counter-action.
//   Use when: modeling geopolitical responses, trade wars, sanctions cycles.
//   Example: Iran RETALIATES against Israel (mechanism: "proxy attacks")
//   Required: actor (str), mechanism (str), probability (0-1)
//
// SUBSTITUTES {cost_premium, feasibility, timeline_days}
//   Semantics: A replaces B when B is unavailable or too expensive.
//   cost_premium: how much more expensive A is than B (0=same, 1=double)
//   feasibility: how practical the substitution is (0-1)
//   Example: LNG SUBSTITUTES Russian pipeline gas (cost_premium: 0.4, feasibility: 0.7)
//   Required: cost_premium, feasibility
//
// SANCTIONED_BY {imposer, mechanism, start_date, scope}
//   Semantics: A is subject to restrictions imposed by B.
//   Use when: modeling economic sanctions, trade restrictions, embargoes.
//   Example: Russia SANCTIONED_BY Western nations (mechanism: "SWIFT exclusion")
//   Required: imposer (str), mechanism (str), start_date (str)
//
// FLOWS_THROUGH {volume, vulnerability, chokepoint}
//   Semantics: Resource A passes through system/location B.
//   vulnerability: how easily this flow can be disrupted (0-1)
//   Use when: modeling supply chains, trade routes, energy networks.
//   Example: Oil FLOWS_THROUGH Strait of Hormuz (vulnerability: 0.8)
//   Required: volume (str), vulnerability (0-1)
//
// BELIEVES {sentiment, actor_count, intensity, source}
//   Semantics: Actor A holds belief/narrative B.
//   sentiment: -1 (very negative) to +1 (very positive)
//   Use when: modeling market sentiment, public opinion, propaganda effects.
//   Example: Market BELIEVES recession_narrative (sentiment: -0.7)
//   Required: sentiment (-1 to 1), actor_count (int)
//
// CORRELATES_WITH {r_squared, lag_days, sample_size}
//   Semantics: A and B move together statistically (NOT causal).
//   Use when: statistical relationship exists but causation not yet validated.
//   This is a hypothesis edge — should be upgraded to CAUSES after DoWhy validation.
//   Required: r_squared (0-1), lag_days (int)
//
// CAUSED_BY {validated, method, confidence, effect_size}
//   Semantics: B was caused by A (reverse direction of CAUSES, post-validation).
//   validated: true only after DoWhy identification passes
//   method: "backdoor" | "frontdoor" | "iv" | "did" | "synthetic_control" | "ols"
//   Use when: DoWhy has formally identified and validated the causal relationship.
//   Required: validated (bool), method (str), confidence (0-1)
//
// SIMULATED_REACTION {agent_type, step, magnitude, trigger}
//   Semantics: Agent A reacted to B in simulation (Mesa ABM output).
//   Use when: storing simulation results in the graph for replay.
//   Required: agent_type (str), step (int), magnitude (float)
//
// MENTIONS {context, relevance}
//   Semantics: Event A mentions/references entity B.
//   Use when: linking raw events to extracted entities.
//   Required: context (str), relevance (0-1)
//
// LOCATED_IN {precision}
//   Semantics: A is geographically located in B.
//   precision: "country" | "region" | "city" | "coordinates"
//   Required: precision (str)
//
// OCCURRED_IN {role}
//   Semantics: Event A occurred in location B.
//   role: "epicenter" | "affected" | "secondary"
//   Required: role (str)

// ─────────────────────────────────────────────────────────────────────────────
// VALIDATION QUERIES (run after seeding to verify schema works)
// ─────────────────────────────────────────────────────────────────────────────
//
// Geopolitical chain:
//   MATCH p=(e:Event)-[:TRIGGERS|CAUSES*1..4]->(m:Metric)
//   WHERE e.domain CONTAINS 'geopolitics'
//   RETURN p LIMIT 5
//
// Resource flow chain:
//   MATCH p=(r:Resource)-[:FLOWS_THROUGH]->(s:System)-[:DISRUPTS]->(m:Metric)
//   RETURN p LIMIT 5
//
// Actor retaliation chain:
//   MATCH p=(a:Actor)-[:RETALIATES]->(b:Actor)-[:ESCALATES_TO]->(e:Event)
//   RETURN p LIMIT 5
//
// Full butterfly chain (4 hops):
//   MATCH p=(e:Event)-[:CAUSES|TRIGGERS|INFLUENCES*1..6]->(end)
//   WHERE e.event_id = $event_id
//   RETURN p ORDER BY length(p) DESC LIMIT 20
// =============================================================================
