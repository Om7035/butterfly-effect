"""Demo API routes — serve hardcoded data so the frontend works without any DB."""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

# ── Hardcoded Fed 2022 causal chain ──────────────────────────────────────────

_DEMO_EVENTS = [
    {
        "event_id": "demo_fed_jun2022",
        "title": "Fed Rate Hike — 75bps",
        "description": "FOMC raises federal funds rate by 75 basis points to combat inflation.",
        "source": "fred",
        "source_url": "https://www.federalreserve.gov/newsevents/pressreleases/monetary20220615a.htm",
        "occurred_at": "2022-06-15T14:00:00",
        "entities": ["Federal Reserve", "FOMC", "US Treasury"],
        "processed": True,
    },
    {
        "event_id": "demo_texas_storm",
        "title": "Texas Winter Storm — ERCOT Grid Failure",
        "description": "Unprecedented winter storm causes widespread power grid failure across Texas.",
        "source": "gdelt",
        "source_url": "https://www.ercot.com",
        "occurred_at": "2021-02-10T06:00:00",
        "entities": ["ERCOT", "Texas", "Natural Gas"],
        "processed": True,
    },
    {
        "event_id": "demo_covid_supply",
        "title": "Semiconductor Shortage Declaration",
        "description": "Global semiconductor shortage declared, impacting auto and electronics production.",
        "source": "gdelt",
        "source_url": "https://www.whitehouse.gov",
        "occurred_at": "2021-09-23T10:00:00",
        "entities": ["TSMC", "Intel", "Auto Industry"],
        "processed": True,
    },
]

_DEMO_CAUSAL_CHAINS = {
    "demo_fed_jun2022": {
        "event_id": "demo_fed_jun2022",
        "nodes": [
            {"id": "n1", "type": "Event",  "label": "Fed Rate Hike",      "description": "75bps FOMC decision", "confidence": 0.99, "value": None, "delta": None},
            {"id": "n2", "type": "Metric", "label": "Treasury Yield",     "description": "10Y Treasury yield",  "confidence": 0.95, "value": 3.45, "delta": 0.75},
            {"id": "n3", "type": "Metric", "label": "Mortgage Rate",      "description": "30-year fixed rate",  "confidence": 0.88, "value": 5.81, "delta": 0.92},
            {"id": "n4", "type": "Entity", "label": "Federal Reserve",    "description": "Central bank",        "confidence": 0.99, "value": None, "delta": None},
            {"id": "n5", "type": "Metric", "label": "Housing Starts",     "description": "New housing units",   "confidence": 0.82, "value": 1559, "delta": -247},
            {"id": "n6", "type": "Entity", "label": "Construction Sector","description": "Building industry",   "confidence": 0.78, "value": None, "delta": None},
            {"id": "n7", "type": "Metric", "label": "Unemployment Rate",  "description": "US unemployment",     "confidence": 0.71, "value": 3.7,  "delta": 0.23},
            {"id": "n8", "type": "Policy", "label": "Monetary Policy",    "description": "Fed policy stance",   "confidence": 0.95, "value": None, "delta": None},
        ],
        "edges": [
            {"id": "e1", "source": "n4", "target": "n1", "type": "CAUSED_BY",    "strength": 0.99, "confidence": 0.99, "latency_hours": 0},
            {"id": "e2", "source": "n1", "target": "n2", "type": "CAUSED_BY",    "strength": 0.92, "confidence": 0.95, "latency_hours": 2},
            {"id": "e3", "source": "n2", "target": "n3", "type": "CAUSED_BY",    "strength": 0.78, "confidence": 0.88, "latency_hours": 48},
            {"id": "e4", "source": "n3", "target": "n5", "type": "CAUSED_BY",    "strength": 0.71, "confidence": 0.82, "latency_hours": 72},
            {"id": "e5", "source": "n5", "target": "n6", "type": "INFLUENCES",   "strength": 0.65, "confidence": 0.75, "latency_hours": 120},
            {"id": "e6", "source": "n6", "target": "n7", "type": "CAUSED_BY",    "strength": 0.54, "confidence": 0.68, "latency_hours": 168},
            {"id": "e7", "source": "n8", "target": "n4", "type": "INFLUENCES",   "strength": 0.85, "confidence": 0.90, "latency_hours": 0},
        ],
        "causal_edges": [
            {
                "edge_id": "e2", "source_node_id": "n1", "target_node_id": "n2",
                "relationship_type": "influences_price", "strength_score": 0.92,
                "latency_hours": 2, "counterfactual_delta": 0.75,
                "confidence_interval": [0.88, 0.96], "evidence_path": ["fred_FEDFUNDS", "fomc_jun2022"],
                "refutation_passed": True,
            },
            {
                "edge_id": "e3", "source_node_id": "n2", "target_node_id": "n3",
                "relationship_type": "influences_price", "strength_score": 0.78,
                "latency_hours": 48, "counterfactual_delta": 0.92,
                "confidence_interval": [0.71, 0.85], "evidence_path": ["fred_MORTGAGE30US"],
                "refutation_passed": True,
            },
            {
                "edge_id": "e4", "source_node_id": "n3", "target_node_id": "n5",
                "relationship_type": "influences_quantity", "strength_score": 0.71,
                "latency_hours": 72, "counterfactual_delta": -254.0,
                "confidence_interval": [0.62, 0.80], "evidence_path": ["fred_HOUST"],
                "refutation_passed": True,
            },
        ],
        "timeline_a": {
            "portfolio_exposure": {"0": 0.60, "24": 0.52, "72": 0.44, "168": 0.37},
            "inventory_level":    {"0": 1000, "24": 980,  "72": 940,  "168": 880},
        },
        "timeline_b": {
            "portfolio_exposure": {"0": 0.60, "24": 0.60, "72": 0.60, "168": 0.60},
            "inventory_level":    {"0": 1000, "24": 1000, "72": 1000, "168": 1000},
        },
        "peak_delta_at_hours": {"portfolio_exposure": 168, "inventory_level": 168},
    },
    "demo_texas_storm": {
        "event_id": "demo_texas_storm",
        "nodes": [
            {"id": "n1", "type": "Event",  "label": "ERCOT Grid Failure",  "description": "Texas power grid collapse", "confidence": 0.99, "value": None, "delta": None},
            {"id": "n2", "type": "Metric", "label": "Natural Gas Price",   "description": "Henry Hub spot price",      "confidence": 0.92, "value": 23.5, "delta": 20.0},
            {"id": "n3", "type": "Entity", "label": "Manufacturing Sector","description": "TX manufacturing output",   "confidence": 0.85, "value": None, "delta": None},
            {"id": "n4", "type": "Metric", "label": "Employment",          "description": "TX employment index",       "confidence": 0.78, "value": 98.2, "delta": -0.26},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2", "type": "CAUSED_BY",  "strength": 0.92, "confidence": 0.92, "latency_hours": 6},
            {"id": "e2", "source": "n1", "target": "n3", "type": "CAUSED_BY",  "strength": 0.85, "confidence": 0.85, "latency_hours": 24},
            {"id": "e3", "source": "n3", "target": "n4", "type": "INFLUENCES", "strength": 0.78, "confidence": 0.78, "latency_hours": 72},
        ],
        "causal_edges": [],
        "timeline_a": {
            "natgas_price": {"0": 3.5, "24": 23.5, "72": 15.0, "168": 5.0},
        },
        "timeline_b": {
            "natgas_price": {"0": 3.5, "24": 3.5, "72": 3.5, "168": 3.5},
        },
        "peak_delta_at_hours": {"natgas_price": 24},
    },
    "demo_covid_supply": {
        "event_id": "demo_covid_supply",
        "nodes": [
            {"id": "n1", "type": "Event",  "label": "Semiconductor Shortage", "description": "Global chip shortage",     "confidence": 0.99, "value": None,  "delta": None},
            {"id": "n2", "type": "Entity", "label": "Auto Industry",           "description": "Vehicle production",       "confidence": 0.92, "value": None,  "delta": None},
            {"id": "n3", "type": "Metric", "label": "Auto Production",         "description": "Monthly units produced",   "confidence": 0.88, "value": 8.2,   "delta": -25.5},
            {"id": "n4", "type": "Metric", "label": "Used Car Prices",         "description": "Manheim Used Vehicle Index","confidence": 0.82, "value": 236.3, "delta": 48.0},
            {"id": "n5", "type": "Metric", "label": "CPI",                     "description": "Consumer Price Index",     "confidence": 0.75, "value": 8.5,   "delta": 1.2},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2", "type": "CAUSED_BY",  "strength": 0.92, "confidence": 0.92, "latency_hours": 48},
            {"id": "e2", "source": "n2", "target": "n3", "type": "CAUSED_BY",  "strength": 0.88, "confidence": 0.88, "latency_hours": 72},
            {"id": "e3", "source": "n3", "target": "n4", "type": "CAUSED_BY",  "strength": 0.82, "confidence": 0.82, "latency_hours": 120},
            {"id": "e4", "source": "n4", "target": "n5", "type": "INFLUENCES", "strength": 0.75, "confidence": 0.75, "latency_hours": 168},
        ],
        "causal_edges": [],
        "timeline_a": {
            "auto_production": {"0": 11.0, "48": 8.2, "120": 7.5, "168": 8.0},
        },
        "timeline_b": {
            "auto_production": {"0": 11.0, "48": 11.0, "120": 11.0, "168": 11.0},
        },
        "peak_delta_at_hours": {"auto_production": 120},
    },
}


@router.get("/events")
async def demo_events():
    """Return demo events list (no DB required)."""
    return {"items": _DEMO_EVENTS, "total": len(_DEMO_EVENTS), "page": 1, "pages": 1}


@router.get("/events/{event_id}")
async def demo_event(event_id: str):
    """Return a single demo event."""
    event = next((e for e in _DEMO_EVENTS if e["event_id"] == event_id), None)
    if not event:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Demo event not found")
    return event


@router.get("/causal/{event_id}")
async def demo_causal_chain(event_id: str):
    """Return demo causal chain (no DB required)."""
    chain = _DEMO_CAUSAL_CHAINS.get(event_id)
    if not chain:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Demo causal chain not found")
    return chain


@router.get("/causal/{event_id}/edges")
async def demo_causal_edges(event_id: str):
    """Return demo causal edges."""
    chain = _DEMO_CAUSAL_CHAINS.get(event_id)
    if not chain:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    return {"event_id": event_id, "edges": chain["edges"]}


@router.get("/causal/{event_id}/diff")
async def demo_counterfactual_diff(event_id: str):
    """Return demo counterfactual diff."""
    chain = _DEMO_CAUSAL_CHAINS.get(event_id)
    if not chain:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "event_id": event_id,
        "timeline_a": chain["timeline_a"],
        "timeline_b": chain["timeline_b"],
        "peak_delta_at_hours": chain["peak_delta_at_hours"],
    }
