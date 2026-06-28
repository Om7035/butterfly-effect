# 🦋 butterfly-effect — MASTER FIX PROMPT
## Single session. Fix everything. Ship a real product.

---

> **How to use this prompt:**
> Paste this ENTIRE file into your AI IDE agent at the start of a new session.
> Do not split it. Do not summarize it. The IDE must read all sections before
> writing a single line of code. Tell the IDE: "Read this completely first,
> then start with Section 1 and work through to Section 7 in order."

---

## WHO YOU ARE

You are simultaneously:
- A **Senior Systems Debugger** who traces root causes, never symptoms
- A **Data Infrastructure Engineer** who knows every free public data API
- A **Python Performance Engineer** who fixes simulation pipelines
- A **Frontend Engineer** who makes data feel alive
- A **Product Engineer** who cares that real users get real answers

You do not fix one thing at a time when problems are connected.
You understand that in this codebase, ONE root cause (simulation exits at
step 2) cascades into FIVE visible symptoms. You fix the root, verify the
symptoms disappear, then fix anything remaining.

You write code that works on the first run. You add logging everywhere.
You do not leave TODOs. You do not write placeholder functions.

---

## WHAT YOU ARE BUILDING

butterfly-effect is a **universal causal inference engine**.

User types ANY question — a war, a pandemic, an earthquake, a tech launch,
a political crisis, an economic shock — and the system:

1. Understands the question (LLM parsing)
2. Fetches real data about it from the open internet (web search + free APIs)
3. Builds a knowledge graph of entities and relationships
4. Runs a multi-agent simulation (100 agents × 168 steps)
5. Computes the counterfactual (what would happen WITHOUT this event)
6. Shows the causal chain — including 3rd and 4th order effects nobody sees

**This is NOT a demo with hardcoded data.**
Every analysis runs live, against real data, for whatever the user asks.

---

## CURRENT STATE (what is broken and why)

### What the UI shows right now:
```
Query: "Pandemic declared — novel pathogen"
Graph: 9 nodes · 2 agents · 2 steps
Causal chain panel: 2 hops (Health → Policy)
All confidence scores: "Low"
Node labels: raw snake_case (infection_rate, mortality_rate)
Graph layout: spaghetti (force-directed, edges crossing nodes)
```

### Root cause (one sentence):
The simulation pipeline exits after 2 steps because of an early termination
condition or wrong default parameters — everything else is a downstream symptom.

### Symptom cascade:
```
Simulation exits at step 2
    ↓
DoWhy receives 2 rows of data (needs minimum 30)
    ↓
Refutation tests fail → all confidence = "Low"
    ↓
DAG has only 2 validated edges → causal chain = 2 hops
    ↓
Graph renders with 2 agent-generated nodes + raw labels
    ↓
Layout algorithm has nothing to work with → spaghetti
```

### Additional problems (not caused by the simulation bug):
- Data fetching is too narrow — only FRED + GDELT, missing huge free sources
- No web search capability — system can't fetch live data about new events
- NER pipeline not extracting enough entities from sparse fetched data
- Node labels show raw variable names instead of human-readable text
- Graph layout uses force-directed instead of hierarchical DAG

---

## SECTION 1 — FIX THE SIMULATION PIPELINE

### Files to fix: `backend/butterfly/simulation/runner.py`, `model.py`, `agents.py`

**Step 1.1 — Fix runner.py**

Find and fix ALL of these issues:

```python
# FIND any of these patterns and fix them:

# BAD: hardcoded low agent counts
n_agents=2  # → change to: n_market=50, n_housing=30, n_supply=15, n_policy=5

# BAD: early termination condition
if model.some_condition():
    break   # → DELETE this entire if block

# BAD: steps parameter not being used
model.run_model(10)  # → change to: model.run_model(steps)

# BAD: missing default
async def run_parallel(event, steps=10):  # → change steps default to 168
```

After fixing, add this guard at the TOP of `run_parallel()`:

```python
# Minimum viable simulation parameters
steps = max(steps, 168)
n_market_agents = max(n_market_agents, 50)
n_housing_agents = max(n_housing_agents, 30)
n_supply_agents = max(n_supply_agents, 15)
n_policy_agents = max(n_policy_agents, 5)

logger.info(f"[SIM START] agents={n_market_agents+n_housing_agents+n_supply_agents+n_policy_agents} steps={steps}")
```

Add this at the END of `run_parallel()`:

```python
actual_steps = result.steps_completed
logger.info(f"[SIM END] steps_completed={actual_steps} timeline_a_len={len(result.timeline_a)}")

# Hard assertion — never return a partial simulation silently
if actual_steps < 100:
    raise SimulationError(f"Simulation terminated early at step {actual_steps}. Check agent step() methods for exceptions.")
```

**Step 1.2 — Fix model.py**

The Mesa model's `step()` method is likely swallowing exceptions silently.
Find any try/except in the step loop and add logging:

```python
def step(self):
    try:
        self.schedule.step()
        self.datacollector.collect(self)
    except Exception as e:
        # THIS is why it exits early — silent exception
        logger.error(f"[MODEL STEP {self.schedule.steps}] Exception: {e}", exc_info=True)
        raise  # re-raise so runner catches it properly
```

**Step 1.3 — Fix agents.py**

Each agent's `step()` method must never raise an unhandled exception.
Wrap each agent step in a safe handler that logs and continues:

```python
def step(self):
    try:
        self._safe_step()
    except Exception as e:
        logger.warning(f"[AGENT {self.unique_id}] step failed at t={self.model.schedule.steps}: {e}")
        # Do NOT re-raise — one agent failure must not kill the simulation

def _safe_step(self):
    # actual step logic here
    ...
```

**Step 1.4 — Write the verification test**

```python
# backend/tests/test_simulation/test_runner_steps.py
async def test_simulation_runs_full_168_steps():
    event = UniversalEvent(
        raw_input="Pandemic declared — novel pathogen",
        title="Pandemic declared",
        domain=["health", "economics"],
        primary_actors=["WHO", "governments"],
        affected_systems=["healthcare", "supply_chain", "labor"],
        geographic_scope=["global"],
        time_horizon="months",
        severity="catastrophic",
        causal_seeds=["hospital_overflow", "lockdowns", "supply_disruption"],
        data_fetch_queries=["pandemic economic impact", "lockdown supply chain"],
        occurred_at=datetime.utcnow(),
        confidence=0.9
    )
    runner = SimulationRunner()
    result = await runner.run_parallel(event, steps=168)
    
    assert result.steps_completed == 168, f"Expected 168 steps, got {result.steps_completed}"
    assert len(result.timeline_a) == 168
    assert len(result.timeline_b) == 168
    assert result.timeline_a != result.timeline_b  # timelines must diverge
    
    # Check divergence happened
    diverged = any(
        abs(result.timeline_a[s].get('healthcare_capacity', 0) - 
            result.timeline_b[s].get('healthcare_capacity', 0)) > 0.01
        for s in range(20, 168)
    )
    assert diverged, "Timeline A and B never diverged — event signal not injected"
```

Run this test. It must pass before moving to Section 2.

```bash
pytest backend/tests/test_simulation/test_runner_steps.py -v -s
```

---

## SECTION 2 — MASSIVE DATA INGESTION UPGRADE

This is the second biggest problem. The system only knows about FRED and GDELT.
For a pandemic question, it gets maybe 5 articles. It needs 50+.

We are adding every major free data source. No paid APIs required.

### 2.1 — Add web search via DuckDuckGo (zero cost, no API key)

```bash
pip install duckduckgo-search
```

Create `backend/butterfly/ingestion/web_search.py`:

```python
"""
Web search ingester using DuckDuckGo — free, no API key, no rate limits (gentle use).
Falls back gracefully if blocked. Returns RawEvidence list.
"""
from duckduckgo_search import DDGS
from butterfly.models.ingestion import RawEvidence
import asyncio
from loguru import logger

async def fetch_duckduckgo(queries: list[str], max_per_query: int = 8) -> list[RawEvidence]:
    """
    Search DuckDuckGo for each query. Returns combined deduplicated results.
    Runs in thread pool (duckduckgo_search is sync).
    """
    results = []
    seen_urls = set()
    
    def _search(query: str) -> list[dict]:
        try:
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_per_query))
        except Exception as e:
            logger.warning(f"[DDGS] Query '{query}' failed: {e}")
            return []
    
    loop = asyncio.get_event_loop()
    for query in queries:
        raw = await loop.run_in_executor(None, _search, query)
        for r in raw:
            url = r.get('href', '')
            if url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(RawEvidence(
                source="duckduckgo",
                title=r.get('title', '')[:200],
                content=r.get('body', '')[:500],
                url=url,
                published_at=None,
                relevance_score=0.7,
                domain_tags=[]
            ))
    
    logger.info(f"[DDGS] Fetched {len(results)} results for {len(queries)} queries")
    return results
```

### 2.2 — Add Wikipedia full-text fetching

Create `backend/butterfly/ingestion/wikipedia.py`:

```python
"""
Wikipedia API ingester — free, no key, excellent for background context on any event.
Fetches full page summaries + related pages for maximum entity extraction.
"""
import httpx
from butterfly.models.ingestion import RawEvidence
from loguru import logger

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary"
WIKI_SEARCH = "https://en.wikipedia.org/w/api.php"

async def fetch_wikipedia(queries: list[str]) -> list[RawEvidence]:
    results = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in queries:
            try:
                # Search for most relevant page
                search_resp = await client.get(WIKI_SEARCH, params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "format": "json",
                    "srlimit": 3
                })
                search_data = search_resp.json()
                pages = search_data.get("query", {}).get("search", [])
                
                for page in pages[:3]:
                    title = page["title"].replace(" ", "_")
                    summary_resp = await client.get(f"{WIKI_API}/{title}")
                    if summary_resp.status_code != 200:
                        continue
                    data = summary_resp.json()
                    extract = data.get("extract", "")
                    if len(extract) < 100:
                        continue
                    results.append(RawEvidence(
                        source="wikipedia",
                        title=data.get("title", title),
                        content=extract[:800],
                        url=data.get("content_urls", {}).get("desktop", {}).get("page"),
                        published_at=None,
                        relevance_score=0.75,
                        domain_tags=[]
                    ))
            except Exception as e:
                logger.warning(f"[WIKI] Query '{query}' failed: {e}")
    
    logger.info(f"[WIKI] Fetched {len(results)} pages")
    return results
```

### 2.3 — Add ReliefWeb API (humanitarian crises — free, no key)

Create `backend/butterfly/ingestion/reliefweb.py`:

```python
"""
ReliefWeb API — UN OCHA's humanitarian data platform.
Free, no API key, covers: natural disasters, conflicts, disease outbreaks,
refugee crises, food insecurity. Perfect for non-financial events.
"""
import httpx
from butterfly.models.ingestion import RawEvidence
from loguru import logger

RELIEFWEB_API = "https://api.reliefweb.int/v1/reports"

async def fetch_reliefweb(queries: list[str]) -> list[RawEvidence]:
    results = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in queries:
            try:
                resp = await client.post(RELIEFWEB_API, json={
                    "query": {"value": query, "operator": "AND"},
                    "fields": {"include": ["title", "body", "date", "url", "source"]},
                    "limit": 10,
                    "sort": ["date:desc"]
                })
                if resp.status_code != 200:
                    continue
                items = resp.json().get("data", [])
                for item in items:
                    fields = item.get("fields", {})
                    body = fields.get("body", "")[:600]
                    results.append(RawEvidence(
                        source="reliefweb",
                        title=fields.get("title", ""),
                        content=body,
                        url=fields.get("url", ""),
                        published_at=None,
                        relevance_score=0.85,  # high quality humanitarian data
                        domain_tags=["humanitarian", "crisis"]
                    ))
            except Exception as e:
                logger.warning(f"[RELIEFWEB] Query '{query}' failed: {e}")
    
    logger.info(f"[RELIEFWEB] Fetched {len(results)} reports")
    return results
```

### 2.4 — Add World Bank API (development indicators — free, no key)

Create `backend/butterfly/ingestion/world_bank.py`:

```python
"""
World Bank Open Data API — free, no key required.
200+ economic/social indicators for 200+ countries.
Ideal for: GDP impact, poverty rates, trade flows, education, health spending.
"""
import httpx
from butterfly.models.ingestion import RawEvidence
from loguru import logger

WB_API = "https://api.worldbank.org/v2"

# Key indicators relevant to causal chains
INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "GDP growth rate",
    "SL.UEM.TOTL.ZS": "Unemployment rate",
    "FP.CPI.TOTL.ZG": "Inflation (CPI)",
    "NE.TRD.GNFS.ZS": "Trade as % of GDP",
    "SH.XPD.CHEX.GD.ZS": "Health expenditure % GDP",
    "EN.ATM.CO2E.PC": "CO2 emissions per capita",
}

async def fetch_world_bank(countries: list[str], indicators: list[str] = None) -> list[RawEvidence]:
    if not countries:
        return []
    if not indicators:
        indicators = list(INDICATORS.keys())[:4]
    
    results = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for country in countries[:5]:  # limit to 5 countries
            for indicator in indicators[:3]:  # limit to 3 indicators
                try:
                    resp = await client.get(
                        f"{WB_API}/country/{country}/indicator/{indicator}",
                        params={"format": "json", "mrv": 5, "per_page": 5}
                    )
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    if len(data) < 2 or not data[1]:
                        continue
                    
                    values = [(d["date"], d["value"]) for d in data[1] if d["value"]]
                    if not values:
                        continue
                    
                    indicator_name = INDICATORS.get(indicator, indicator)
                    content = f"{country} {indicator_name}: " + ", ".join(
                        f"{yr}: {val:.2f}" for yr, val in values
                    )
                    results.append(RawEvidence(
                        source="world_bank",
                        title=f"{country} — {indicator_name}",
                        content=content,
                        url=f"https://data.worldbank.org/indicator/{indicator}?locations={country}",
                        published_at=None,
                        relevance_score=0.8,
                        domain_tags=["economics", "development"]
                    ))
                except Exception as e:
                    logger.warning(f"[WB] {country}/{indicator} failed: {e}")
    
    logger.info(f"[WORLD_BANK] Fetched {len(results)} indicators")
    return results
```

### 2.5 — Add ACLED (Armed Conflict Location & Event Data — free with registration)

Create `backend/butterfly/ingestion/acled.py`:

```python
"""
ACLED — Armed Conflict Location & Event Data project.
Free API (requires free registration at acleddata.com).
Covers: political violence, protests, battles, explosions globally.
Falls back to GDELT if no ACLED key configured.
"""
import httpx
from butterfly.models.ingestion import RawEvidence
from butterfly.config import settings
from loguru import logger

ACLED_API = "https://api.acleddata.com/acled/read"

async def fetch_acled(queries: list[str]) -> list[RawEvidence]:
    if not settings.ACLED_API_KEY or not settings.ACLED_EMAIL:
        logger.info("[ACLED] No credentials configured — skipping (get free key at acleddata.com)")
        return []
    
    results = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in queries[:3]:
            try:
                resp = await client.get(ACLED_API, params={
                    "key": settings.ACLED_API_KEY,
                    "email": settings.ACLED_EMAIL,
                    "event_date": "2020-01-01|2026-12-31",
                    "event_date_where": "BETWEEN",
                    "limit": 10,
                    "fields": "event_date|event_type|country|actor1|notes|fatalities",
                    "region": _query_to_region(query),
                })
                if resp.status_code != 200:
                    continue
                for event in resp.json().get("data", []):
                    results.append(RawEvidence(
                        source="acled",
                        title=f"{event.get('event_type')} in {event.get('country')}",
                        content=event.get('notes', '')[:500],
                        url=None,
                        published_at=None,
                        relevance_score=0.9,
                        domain_tags=["conflict", "geopolitics", "military"]
                    ))
            except Exception as e:
                logger.warning(f"[ACLED] Query '{query}' failed: {e}")
    
    logger.info(f"[ACLED] Fetched {len(results)} conflict events")
    return results

def _query_to_region(query: str) -> str:
    query_lower = query.lower()
    if any(w in query_lower for w in ["middle east", "israel", "gaza", "iran", "iraq", "syria"]):
        return "Middle East"
    if any(w in query_lower for w in ["ukraine", "russia", "europe"]):
        return "Europe"
    if any(w in query_lower for w in ["africa", "ethiopia", "nigeria", "sudan"]):
        return "Africa"
    if any(w in query_lower for w in ["asia", "china", "taiwan", "india"]):
        return "Asia"
    return ""
```

### 2.6 — Add Open-Meteo (climate/weather — free, no key)

Create `backend/butterfly/ingestion/open_meteo.py`:

```python
"""
Open-Meteo — free weather and climate API, no key required.
Useful for: climate events, natural disasters, agricultural impact.
"""
import httpx
from butterfly.models.ingestion import RawEvidence
from loguru import logger

OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
GEOCODING_API = "https://geocoding-api.open-meteo.com/v1/search"

async def fetch_open_meteo(locations: list[str]) -> list[RawEvidence]:
    results = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for location in locations[:3]:
            try:
                # Get coordinates
                geo = await client.get(GEOCODING_API, params={"name": location, "count": 1})
                geo_data = geo.json().get("results", [])
                if not geo_data:
                    continue
                
                lat, lon = geo_data[0]["latitude"], geo_data[0]["longitude"]
                
                # Get weather data
                weather = await client.get(OPEN_METEO_API, params={
                    "latitude": lat, "longitude": lon,
                    "daily": "temperature_2m_max,precipitation_sum,windspeed_10m_max",
                    "forecast_days": 7,
                    "timezone": "auto"
                })
                data = weather.json().get("daily", {})
                temps = data.get("temperature_2m_max", [])
                precip = data.get("precipitation_sum", [])
                
                if temps:
                    content = (f"{location} weather: max temps {min(temps):.1f}–{max(temps):.1f}°C, "
                               f"total precip {sum(p for p in precip if p):.1f}mm over 7 days")
                    results.append(RawEvidence(
                        source="open_meteo",
                        title=f"Weather data — {location}",
                        content=content,
                        url=None,
                        published_at=None,
                        relevance_score=0.6,
                        domain_tags=["climate", "weather", "environment"]
                    ))
            except Exception as e:
                logger.warning(f"[OPEN_METEO] Location '{location}' failed: {e}")
    
    logger.info(f"[OPEN_METEO] Fetched {len(results)} location forecasts")
    return results
```

### 2.7 — Add RSS feed aggregator (free, universal coverage)

Create `backend/butterfly/ingestion/rss_feeds.py`:

```python
"""
RSS feed aggregator — free, real-time, covers any topic.
Aggregates from major free RSS feeds filtered by topic.
Uses feedparser (pip install feedparser).
"""
import feedparser
import asyncio
from butterfly.models.ingestion import RawEvidence
from loguru import logger
from datetime import datetime

# Free RSS feeds organized by domain — add more as needed
DOMAIN_FEEDS = {
    "geopolitics": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.reuters.com/Reuters/worldNews",
    ],
    "economics": [
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml",
        "https://www.economist.com/finance-and-economics/rss.xml",
    ],
    "technology": [
        "https://techcrunch.com/feed/",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.wired.com/feed/rss",
    ],
    "health": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
        "https://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.who.int/rss-feeds/news-english.xml",
    ],
    "climate": [
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "https://www.climate.gov/feeds/news_rss.xml",
    ],
    "energy": [
        "https://oilprice.com/rss/main",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ],
}

async def fetch_rss(domains: list[str], keywords: list[str]) -> list[RawEvidence]:
    feed_urls = []
    for domain in domains:
        feed_urls.extend(DOMAIN_FEEDS.get(domain, []))
    
    if not feed_urls:
        feed_urls = DOMAIN_FEEDS["geopolitics"]  # fallback
    
    feed_urls = list(set(feed_urls))[:8]  # max 8 feeds
    results = []
    
    def _parse_feed(url: str) -> list[dict]:
        try:
            return feedparser.parse(url).entries[:5]
        except Exception:
            return []
    
    loop = asyncio.get_event_loop()
    all_entries = []
    for url in feed_urls:
        entries = await loop.run_in_executor(None, _parse_feed, url)
        all_entries.extend(entries)
    
    # Filter by keyword relevance
    keywords_lower = [k.lower() for k in keywords]
    for entry in all_entries:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        combined = (title + " " + summary).lower()
        
        if not any(kw in combined for kw in keywords_lower):
            continue
        
        results.append(RawEvidence(
            source="rss",
            title=title[:200],
            content=summary[:500],
            url=entry.get("link", ""),
            published_at=None,
            relevance_score=0.65,
            domain_tags=domains
        ))
    
    logger.info(f"[RSS] Fetched {len(results)} relevant articles from {len(feed_urls)} feeds")
    return results
```

### 2.8 — Add OpenAlex (academic research — free, no key)

Create `backend/butterfly/ingestion/openalex.py`:

```python
"""
OpenAlex — free, open academic knowledge graph (replaced Microsoft Academic).
200M+ research papers. Useful for: scientific consensus on any causal claim,
validating that our causal chains match peer-reviewed literature.
"""
import httpx
from butterfly.models.ingestion import RawEvidence
from loguru import logger

OPENALEX_API = "https://api.openalex.org/works"

async def fetch_openalex(queries: list[str]) -> list[RawEvidence]:
    results = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in queries[:3]:
            try:
                resp = await client.get(OPENALEX_API, params={
                    "search": query,
                    "filter": "cited_by_count:>50",  # only well-cited papers
                    "sort": "cited_by_count:desc",
                    "per-page": 5,
                    "select": "title,abstract_inverted_index,doi,publication_year,cited_by_count"
                })
                if resp.status_code != 200:
                    continue
                
                for work in resp.json().get("results", []):
                    title = work.get("title", "")
                    abstract_index = work.get("abstract_inverted_index", {})
                    
                    # Reconstruct abstract from inverted index
                    if abstract_index:
                        words = {pos: word for word, positions in abstract_index.items()
                                 for pos in positions}
                        abstract = " ".join(words[i] for i in sorted(words.keys()))[:500]
                    else:
                        abstract = ""
                    
                    if not abstract:
                        continue
                    
                    results.append(RawEvidence(
                        source="openalex",
                        title=title[:200],
                        content=f"[Academic, {work.get('publication_year')}, {work.get('cited_by_count')} citations] {abstract}",
                        url=f"https://doi.org/{work.get('doi', '')}" if work.get('doi') else None,
                        published_at=None,
                        relevance_score=0.9,  # academic = high credibility
                        domain_tags=["research", "academic"]
                    ))
            except Exception as e:
                logger.warning(f"[OPENALEX] Query '{query}' failed: {e}")
    
    logger.info(f"[OPENALEX] Fetched {len(results)} papers")
    return results
```

### 2.9 — Upgrade universal_fetcher.py to use ALL sources

Completely rewrite `backend/butterfly/ingestion/universal_fetcher.py`:

```python
"""
UniversalFetcher — orchestrates all data sources for any event domain.
Runs all relevant fetchers concurrently. Returns top 60 deduplicated results.
Requires ZERO API keys for basic operation (all free sources).
Optional API keys unlock: ACLED (conflict), NewsAPI (news quality).
"""
import asyncio
import hashlib
import json
from butterfly.models.event import UniversalEvent
from butterfly.models.ingestion import RawEvidence
from butterfly.db.redis import get_redis
from butterfly.ingestion import (
    fred, gdelt, wikipedia, reliefweb, world_bank,
    acled, open_meteo, rss_feeds, openalex, web_search
)
from loguru import logger

# Domain → which fetchers to call
# Order matters: higher quality sources first
DOMAIN_FETCHER_MAP = {
    "geopolitics": [
        web_search.fetch_duckduckgo,
        rss_feeds.fetch_rss,
        reliefweb.fetch_reliefweb,
        acled.fetch_acled,
        wikipedia.fetch_wikipedia,
        gdelt.fetch_gdelt,
    ],
    "military": [
        web_search.fetch_duckduckgo,
        acled.fetch_acled,
        reliefweb.fetch_reliefweb,
        gdelt.fetch_gdelt,
        wikipedia.fetch_wikipedia,
    ],
    "economics": [
        fred.fetch_fred,
        world_bank.fetch_world_bank,
        web_search.fetch_duckduckgo,
        rss_feeds.fetch_rss,
        wikipedia.fetch_wikipedia,
        openalex.fetch_openalex,
    ],
    "financial_markets": [
        fred.fetch_fred,
        web_search.fetch_duckduckgo,
        rss_feeds.fetch_rss,
        wikipedia.fetch_wikipedia,
    ],
    "health": [
        web_search.fetch_duckduckgo,
        reliefweb.fetch_reliefweb,
        rss_feeds.fetch_rss,
        wikipedia.fetch_wikipedia,
        openalex.fetch_openalex,
        world_bank.fetch_world_bank,
    ],
    "climate": [
        open_meteo.fetch_open_meteo,
        web_search.fetch_duckduckgo,
        rss_feeds.fetch_rss,
        wikipedia.fetch_wikipedia,
        openalex.fetch_openalex,
    ],
    "environment": [
        open_meteo.fetch_open_meteo,
        reliefweb.fetch_reliefweb,
        web_search.fetch_duckduckgo,
        wikipedia.fetch_wikipedia,
    ],
    "technology": [
        web_search.fetch_duckduckgo,
        rss_feeds.fetch_rss,
        wikipedia.fetch_wikipedia,
        openalex.fetch_openalex,
    ],
    "humanitarian": [
        reliefweb.fetch_reliefweb,
        web_search.fetch_duckduckgo,
        rss_feeds.fetch_rss,
        wikipedia.fetch_wikipedia,
        world_bank.fetch_world_bank,
    ],
    "energy": [
        fred.fetch_fred,
        web_search.fetch_duckduckgo,
        rss_feeds.fetch_rss,
        wikipedia.fetch_wikipedia,
        gdelt.fetch_gdelt,
    ],
    "logistics": [
        web_search.fetch_duckduckgo,
        gdelt.fetch_gdelt,
        rss_feeds.fetch_rss,
        wikipedia.fetch_wikipedia,
    ],
    "political": [
        web_search.fetch_duckduckgo,
        gdelt.fetch_gdelt,
        rss_feeds.fetch_rss,
        wikipedia.fetch_wikipedia,
        acled.fetch_acled,
    ],
    "social": [
        web_search.fetch_duckduckgo,
        rss_feeds.fetch_rss,
        gdelt.fetch_gdelt,
        wikipedia.fetch_wikipedia,
    ],
    "trade": [
        world_bank.fetch_world_bank,
        fred.fetch_fred,
        web_search.fetch_duckduckgo,
        wikipedia.fetch_wikipedia,
    ],
}

# Default fetchers if domain not recognized
DEFAULT_FETCHERS = [
    web_search.fetch_duckduckgo,
    wikipedia.fetch_wikipedia,
    gdelt.fetch_gdelt,
    rss_feeds.fetch_rss,
]


class UniversalFetcher:
    
    async def fetch(self, event: UniversalEvent) -> list[RawEvidence]:
        # Check cache first
        cache_key = self._cache_key(event)
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            logger.info(f"[FETCHER] Cache hit for '{event.title}'")
            return [RawEvidence(**r) for r in json.loads(cached)]
        
        # Determine which fetchers to use
        fetchers = set()
        for domain in event.domain:
            for fetcher in DOMAIN_FETCHER_MAP.get(domain, DEFAULT_FETCHERS):
                fetchers.add(fetcher)
        
        if not fetchers:
            fetchers = set(DEFAULT_FETCHERS)
        
        logger.info(f"[FETCHER] Running {len(fetchers)} fetchers for domains: {event.domain}")
        
        # Build arguments for each fetcher type
        queries = event.data_fetch_queries + [event.title]
        locations = event.geographic_scope
        domains = event.domain
        countries = [loc for loc in locations if len(loc) <= 3]  # ISO codes
        keywords = event.primary_actors + [event.title]
        
        # Run all fetchers concurrently
        tasks = []
        for fetcher in fetchers:
            name = fetcher.__name__
            if "world_bank" in name:
                tasks.append(fetcher(countries or ["US", "GB"]))
            elif "open_meteo" in name:
                tasks.append(fetcher(locations or ["Global"]))
            elif "rss" in name:
                tasks.append(fetcher(domains, keywords))
            else:
                tasks.append(fetcher(queries))
        
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten, filter exceptions, deduplicate
        all_results: list[RawEvidence] = []
        seen_titles = set()
        for result in results_nested:
            if isinstance(result, Exception):
                logger.warning(f"[FETCHER] A fetcher failed: {result}")
                continue
            for item in result:
                if item.title in seen_titles:
                    continue
                seen_titles.add(item.title)
                all_results.append(item)
        
        # Score relevance based on keyword presence
        for item in all_results:
            combined = (item.title + " " + item.content).lower()
            matches = sum(1 for actor in event.primary_actors if actor.lower() in combined)
            item.relevance_score = min(item.relevance_score + (matches * 0.05), 1.0)
        
        # Sort by relevance, take top 60
        all_results.sort(key=lambda r: r.relevance_score, reverse=True)
        final = all_results[:60]
        
        logger.info(f"[FETCHER] Total: {len(all_results)} raw → {len(final)} after dedup+rank")
        
        # Must have minimum data to proceed
        if len(final) < 5:
            logger.error(f"[FETCHER] Only {len(final)} results — graph will be too sparse")
        
        # Cache for 6 hours
        await redis.setex(cache_key, 21600, json.dumps([r.dict() for r in final]))
        
        return final
    
    def _cache_key(self, event: UniversalEvent) -> str:
        key_str = event.title + "|".join(sorted(event.domain))
        return f"fetch:{hashlib.md5(key_str.encode()).hexdigest()}"
```

### 2.10 — Update requirements.txt

Add these lines to `backend/requirements.txt`:

```
duckduckgo-search>=6.0.0
feedparser>=6.0.10
```

These are the only new dependencies. Everything else (httpx, asyncio) is already installed.

### 2.11 — Update .env.example with new optional keys

```bash
# Optional — get free key at acleddata.com (takes 5 minutes)
ACLED_API_KEY=
ACLED_EMAIL=

# Optional — $50/mo for higher quality news
NEWS_API_KEY=

# Required — get free key at fred.stlouisfed.org
FRED_API_KEY=
```

---

## SECTION 3 — FIX THE NER PIPELINE FOR ANY DOMAIN

The spaCy pipeline extracts entities but produces too few for non-financial events.
Fix `backend/butterfly/extraction/ner.py`:

```python
# ADD these entity type mappings for universal domains:

ENTITY_TYPE_MAP = {
    # Existing
    "ORG": "Actor",
    "GPE": "Location",
    "MONEY": "Metric",
    "PERCENT": "Metric",
    "LAW": "Policy",
    "EVENT": "Event",
    "PERSON": "Actor",
    # ADD THESE:
    "NORP": "Actor",       # nationalities, religious/political groups → Actor
    "FAC": "Location",     # facilities (hospitals, airports) → Location
    "LOC": "Location",     # non-GPE locations (mountains, rivers) → Location
    "PRODUCT": "Actor",    # products/technologies treated as actors
    "QUANTITY": "Metric",  # measurements → Metric
    "CARDINAL": "Metric",  # numbers → Metric (if in context of count data)
    "DATE": None,          # ignore pure date entities
    "TIME": None,          # ignore pure time entities
    "ORDINAL": None,       # ignore ordinal numbers
}

# ADD: After spaCy extraction, supplement with domain keyword extraction
DOMAIN_KEYWORDS = {
    "health": ["pandemic", "virus", "pathogen", "outbreak", "mortality", "infection",
               "vaccine", "hospital", "healthcare", "WHO", "epidemic", "quarantine",
               "lockdown", "immunity", "transmission"],
    "geopolitics": ["war", "conflict", "sanctions", "military", "alliance", "treaty",
                    "ceasefire", "invasion", "occupation", "diplomacy", "NATO", "UN"],
    "economics": ["GDP", "inflation", "recession", "trade", "tariff", "supply chain",
                  "unemployment", "interest rate", "central bank", "fiscal", "monetary"],
    "climate": ["temperature", "emissions", "flood", "drought", "hurricane", "wildfire",
                "sea level", "carbon", "renewable", "fossil fuel", "IPCC"],
    "technology": ["AI", "semiconductor", "chip", "algorithm", "platform", "startup",
                   "automation", "robotics", "quantum", "cybersecurity"],
}

def extract_domain_entities(text: str, domains: list[str]) -> list[ExtractedEntity]:
    """Supplement spaCy NER with domain-specific keyword matching."""
    entities = []
    text_lower = text.lower()
    for domain in domains:
        for keyword in DOMAIN_KEYWORDS.get(domain, []):
            if keyword.lower() in text_lower:
                entities.append(ExtractedEntity(
                    text=keyword,
                    label="Metric" if keyword[0].islower() else "Actor",
                    start=text_lower.find(keyword.lower()),
                    end=text_lower.find(keyword.lower()) + len(keyword),
                    confidence=0.6
                ))
    return entities
```

Also add this minimum entity count check in `graph_builder.py`:

```python
async def process_universal_event(self, event: UniversalEvent, evidence: list[RawEvidence]):
    # ... existing processing ...
    
    node_count = await self._count_nodes_for_event(event.event_id)
    
    if node_count < 6:
        logger.warning(f"[GRAPH] Only {node_count} nodes extracted — graph too sparse for meaningful causal analysis")
        logger.warning("[GRAPH] Possible causes: NER missed entities, fetcher returned too few articles")
        # Force extract entities from event's own causal_seeds
        for seed in event.causal_seeds:
            await self.upsert_entity(ExtractedEntity(
                text=seed.replace("_", " ").title(),
                label="Metric",
                start=0, end=len(seed),
                confidence=0.5
            ))
        logger.info(f"[GRAPH] Added {len(event.causal_seeds)} seed entities from event parser")
```

---

## SECTION 4 — FIX THE CAUSAL CHAIN DEPTH

The causal chain panel shows only 2 hops. Target: 5-6 hops for complex events.

Fix `backend/butterfly/causal/dag.py` — add domain-specific DAG seed templates:

```python
"""
Domain templates provide a structural starting point for the DAG.
These are based on well-established causal mechanisms in each domain.
They are MERGED with graph-derived edges, not replaced by them.
All edge weights start at 0.5 (weak prior) — data overrides them.
"""

DOMAIN_TEMPLATES = {
    "health": {
        "edges": [
            ("pathogen_spread", "infection_rate", 24),
            ("infection_rate", "healthcare_capacity", 48),
            ("healthcare_capacity", "mortality_rate", 72),
            ("infection_rate", "mobility_restriction", 48),
            ("mobility_restriction", "supply_chain_disruption", 168),
            ("supply_chain_disruption", "consumer_spending", 336),
            ("consumer_spending", "unemployment_rate", 720),
            ("mobility_restriction", "government_debt", 720),
            ("government_debt", "inflation_rate", 2160),
        ]
    },
    "geopolitics": {
        "edges": [
            ("military_action", "civilian_displacement", 24),
            ("military_action", "oil_supply_disruption", 72),
            ("oil_supply_disruption", "energy_prices", 24),
            ("energy_prices", "inflation_rate", 168),
            ("civilian_displacement", "refugee_flows", 168),
            ("refugee_flows", "host_country_economy", 720),
            ("military_action", "trade_route_disruption", 48),
            ("trade_route_disruption", "global_supply_chain", 168),
            ("global_supply_chain", "consumer_prices", 336),
        ]
    },
    "economics": {
        "edges": [
            ("interest_rate_change", "bond_prices", 24),
            ("bond_prices", "mortgage_rates", 48),
            ("mortgage_rates", "housing_starts", 336),
            ("housing_starts", "construction_employment", 720),
            ("interest_rate_change", "exchange_rate", 24),
            ("exchange_rate", "export_competitiveness", 168),
            ("export_competitiveness", "trade_balance", 720),
        ]
    },
    "climate": {
        "edges": [
            ("extreme_weather_event", "infrastructure_damage", 0),
            ("infrastructure_damage", "displacement", 24),
            ("displacement", "food_security", 168),
            ("extreme_weather_event", "agricultural_loss", 24),
            ("agricultural_loss", "food_prices", 168),
            ("food_prices", "social_unrest", 336),
            ("infrastructure_damage", "insurance_claims", 48),
            ("insurance_claims", "reinsurance_markets", 168),
        ]
    },
    "technology": {
        "edges": [
            ("tech_breakthrough", "incumbent_disruption", 168),
            ("incumbent_disruption", "employment_shift", 720),
            ("tech_breakthrough", "investment_flows", 72),
            ("investment_flows", "startup_ecosystem", 720),
            ("tech_breakthrough", "regulatory_response", 336),
            ("regulatory_response", "market_structure", 2160),
        ]
    },
}


def merge_template_with_graph(dag, event_domains: list[str]) -> dag:
    """
    Add template edges to DAG as weak priors.
    Only adds edges between nodes that DON'T already exist in the graph —
    this supplements sparse graphs without overriding real extracted data.
    """
    existing_nodes = set(dag.nodes())
    
    for domain in event_domains:
        template = DOMAIN_TEMPLATES.get(domain, {})
        for source, target, latency_hours in template.get("edges", []):
            # Only add if both nodes can be connected to existing graph
            # or if graph is very sparse (< 5 nodes)
            if len(existing_nodes) < 5 or (source in existing_nodes or target in existing_nodes):
                if not dag.has_edge(source, target):
                    dag.add_edge(source, target)
                    dag.nodes[source if source in dag else target]['template'] = True
                    dag.nodes[source if source in dag else target]['latency_hours'] = latency_hours
    
    return dag
```

---

## SECTION 5 — FIX FRONTEND NODE LABELS AND GRAPH LAYOUT

### 5.1 — Fix node label humanization in `frontend/lib/graph.ts`

```typescript
// Add this complete mapping + fallback function

const NODE_LABEL_MAP: Record<string, string> = {
  // Health domain
  infection_rate: "Infection rate",
  mortality_rate: "Mortality rate",
  healthcare_capacity: "Hospital capacity",
  mobility_restriction: "Movement restrictions",
  vaccine_coverage: "Vaccine coverage",
  government_debt: "Government debt",
  supply_chain_disruption: "Supply chain disruption",
  consumer_spending: "Consumer spending",
  unemployment_rate: "Unemployment rate",
  // Geopolitics domain
  military_action: "Military action",
  civilian_displacement: "Civilian displacement",
  oil_supply_disruption: "Oil supply disruption",
  energy_prices: "Energy prices",
  refugee_flows: "Refugee flows",
  trade_route_disruption: "Trade route disruption",
  // Economics domain
  interest_rate_change: "Interest rate change",
  bond_prices: "Bond prices",
  mortgage_rates: "Mortgage rates",
  housing_starts: "Housing starts",
  construction_employment: "Construction jobs",
  exchange_rate: "Exchange rate",
  // Climate domain
  extreme_weather_event: "Extreme weather",
  infrastructure_damage: "Infrastructure damage",
  agricultural_loss: "Agricultural loss",
  food_prices: "Food prices",
  social_unrest: "Social unrest",
  insurance_claims: "Insurance claims",
  // Technology domain
  tech_breakthrough: "Technology breakthrough",
  incumbent_disruption: "Market disruption",
  employment_shift: "Employment shift",
  investment_flows: "Investment flows",
  regulatory_response: "Regulatory response",
}

export function humanizeNodeLabel(raw: string): string {
  if (NODE_LABEL_MAP[raw]) return NODE_LABEL_MAP[raw]
  // Fallback: replace underscores, title case first word only
  return raw
    .replace(/_/g, ' ')
    .replace(/^\w/, c => c.toUpperCase())
}

// Apply this everywhere nodes are built:
// BEFORE: { id: node.id, data: { label: node.id } }
// AFTER:  { id: node.id, data: { label: humanizeNodeLabel(node.id) } }
```

### 5.2 — Switch graph layout from force-directed to Dagre

In `frontend/components/CausalGraph.tsx`:

```bash
npm install @dagrejs/dagre @types/dagre
```

```typescript
import dagre from '@dagrejs/dagre'

const NODE_WIDTH = 180
const NODE_HEIGHT = 60

function applyDagreLayout(
  nodes: Node[],
  edges: Edge[],
  direction: 'TB' | 'LR' = 'TB'
): Node[] {
  const g = new dagre.graphlib.Graph()
  g.setGraph({
    rankdir: direction,
    nodesep: 60,    // horizontal spacing
    ranksep: 100,   // vertical spacing between ranks
    marginx: 40,
    marginy: 40,
    acyclicer: 'greedy',  // handle cycles gracefully
    ranker: 'network-simplex'
  })
  g.setDefaultEdgeLabel(() => ({}))
  
  nodes.forEach(node => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  })
  
  edges.forEach(edge => {
    // Only add edge if both nodes exist
    if (g.hasNode(edge.source) && g.hasNode(edge.target)) {
      g.setEdge(edge.source, edge.target)
    }
  })
  
  dagre.layout(g)
  
  return nodes.map(node => {
    const nodeWithPosition = g.node(node.id)
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    }
  })
}

// Call this before passing nodes to <ReactFlow>:
// const layoutedNodes = applyDagreLayout(nodes, edges)
```

### 5.3 — Fix confidence display in the causal chain panel

In `frontend/components/EvidencePanel.tsx` or wherever confidence is shown:

```typescript
function getConfidenceLabel(score: number): { label: string; color: string } {
  if (score >= 0.7) return { label: "High",   color: "#22c55e" }  // green
  if (score >= 0.4) return { label: "Medium", color: "#f59e0b" }  // amber
  if (score >= 0.2) return { label: "Low",    color: "#ef4444" }  // red
  return                    { label: "Minimal", color: "#6b7280" } // gray
}

// Add a tooltip explaining what confidence means:
// "Confidence reflects how well this causal relationship survived 
//  statistical refutation tests against real data."
```

---

## SECTION 6 — ADD MINIMUM DATA VALIDATION GATE

This prevents the pipeline from producing garbage output when data is sparse.

Add to `backend/butterfly/pipeline/orchestrator.py`:

```python
class DataQualityGate:
    """
    Checks data quality at each pipeline stage.
    Aborts early with a clear message instead of producing bad output.
    """
    
    MIN_EVIDENCE_ITEMS = 8    # minimum articles/data points
    MIN_GRAPH_NODES = 6       # minimum knowledge graph nodes
    MIN_GRAPH_EDGES = 5       # minimum relationships
    MIN_SIM_STEPS = 100       # minimum simulation steps
    MIN_CAUSAL_HOPS = 3       # minimum causal chain depth
    
    def check_evidence(self, evidence: list) -> None:
        if len(evidence) < self.MIN_EVIDENCE_ITEMS:
            raise InsufficientDataError(
                f"Only {len(evidence)} data sources found (minimum {self.MIN_EVIDENCE_ITEMS}). "
                f"The system needs more information about this event to trace effects reliably. "
                f"Try adding more specific search terms or check your API keys."
            )
    
    def check_graph(self, node_count: int, edge_count: int) -> None:
        if node_count < self.MIN_GRAPH_NODES:
            raise InsufficientDataError(
                f"Knowledge graph has only {node_count} entities (minimum {self.MIN_GRAPH_NODES}). "
                f"The NLP pipeline couldn't extract enough entities from the fetched data."
            )
    
    def check_simulation(self, steps_completed: int) -> None:
        if steps_completed < self.MIN_SIM_STEPS:
            raise SimulationError(
                f"Simulation completed only {steps_completed} steps (minimum {self.MIN_SIM_STEPS}). "
                f"Check simulation/runner.py for early termination conditions."
            )
    
    def check_causal_chain(self, hop_count: int) -> None:
        if hop_count < self.MIN_CAUSAL_HOPS:
            logger.warning(
                f"Causal chain has only {hop_count} hops (target: {self.MIN_CAUSAL_HOPS}+). "
                f"This may indicate sparse graph data or limited domain template coverage."
            )
            # Warning only — don't abort, show what we have
```

---

## SECTION 7 — VERIFICATION CHECKLIST

After ALL sections are complete, run these checks IN ORDER.
Do not skip any check. Each must pass before the next.

### Check 1 — Simulation runs correctly
```bash
cd backend
pytest tests/test_simulation/test_runner_steps.py -v -s

# Expected output:
# PASSED — steps_completed=168, timelines diverge
```

### Check 2 — Data fetching returns real results
```bash
python -c "
import asyncio
from butterfly.ingestion.universal_fetcher import UniversalFetcher
from butterfly.models.event import UniversalEvent
from datetime import datetime

event = UniversalEvent(
    raw_input='Pandemic declared — novel pathogen',
    title='Pandemic declared',
    domain=['health', 'economics'],
    primary_actors=['WHO', 'governments'],
    affected_systems=['healthcare', 'supply_chain'],
    geographic_scope=['global'],
    time_horizon='months',
    severity='catastrophic',
    causal_seeds=['hospital_overflow', 'lockdowns'],
    data_fetch_queries=['pandemic economic impact 2024', 'lockdown supply chain effects'],
    occurred_at=datetime.utcnow(),
    confidence=0.9
)

async def test():
    fetcher = UniversalFetcher()
    results = await fetcher.fetch(event)
    print(f'Evidence items: {len(results)}')
    print(f'Sources: {set(r.source for r in results)}')
    assert len(results) >= 8, f'Too few results: {len(results)}'
    print('CHECK 2 PASSED')

asyncio.run(test())
"
```

### Check 3 — Full pipeline produces deep causal chain
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "Pandemic declared — novel pathogen with high mortality rate"}' \
  | python -c "
import sys, json
data = json.load(sys.stdin)
hops = data['causal_chain']['total_hops']
steps = data['simulation']['steps_completed']
nodes = data['graph_stats']['node_count']
sources = data['evidence_sources']
print(f'Hops: {hops} (need >= 4)')
print(f'Steps: {steps} (need >= 168)')
print(f'Nodes: {nodes} (need >= 6)')
print(f'Sources: {sources}')
assert hops >= 4, f'FAIL: only {hops} hops'
assert steps >= 168, f'FAIL: only {steps} steps'
assert nodes >= 6, f'FAIL: only {nodes} nodes'
print('CHECK 3 PASSED — full pipeline working')
"
```

### Check 4 — Test with a completely different domain (war)
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "Full-scale war breaks out between two nuclear powers"}' \
  | python -c "
import sys, json
data = json.load(sys.stdin)
domains = data['event']['domain']
hops = data['causal_chain']['total_hops']
print(f'Domains detected: {domains}')
print(f'Chain depth: {hops}')
assert 'geopolitics' in domains or 'military' in domains, 'Domain not detected correctly'
assert hops >= 3, f'Chain too shallow: {hops}'
print('CHECK 4 PASSED — geopolitics domain works')
"
```

### Check 5 — Test with tech domain
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"question": "OpenAI releases AGI that passes all human benchmarks"}' \
  | python -c "
import sys, json
data = json.load(sys.stdin)
domains = data['event']['domain']
print(f'Domains detected: {domains}')
assert 'technology' in domains, f'Technology domain not detected: {domains}'
print('CHECK 5 PASSED — technology domain works')
"
```

### Check 6 — Verify UI shows humanized labels
```
Open http://localhost:3000
Type: "Pandemic declared — novel pathogen"
Wait for analysis to complete

VERIFY visually:
[ ] Nodes show: "Hospital capacity" NOT "healthcare_capacity"
[ ] Nodes show: "Consumer spending" NOT "consumer_spending"
[ ] Graph flows top-to-bottom (DAG layout, not spaghetti)
[ ] Causal chain panel shows 4+ hops
[ ] At least one confidence score is Medium or High (not all Low)
[ ] Stats bar shows: "X nodes · 100 agents · 168 steps"
```

---

## WHAT DONE LOOKS LIKE

When all 6 checks pass, the system will:

1. Accept any question from any domain
2. Fetch 30-60 real data points from 5+ free sources
3. Build a knowledge graph with 8+ nodes
4. Run 100 agents for 168 steps in under 2 seconds
5. Produce a causal chain with 4-6 hops
6. Show human-readable node labels in a clean top-down layout
7. Display meaningful confidence scores based on real DoWhy validation
8. Generate insights that include 3rd and 4th order effects

The system works equally well for:
- "War breaks out in Taiwan strait"
- "Category 5 hurricane destroys Miami"
- "Nvidia releases chip 100x faster than current gen"
- "New pandemic strain detected — 40% mortality rate"
- "Fed raises rates 200bps in emergency session"
- "Massive earthquake hits Tokyo"
- "Oil hits $200 per barrel"
- "Social media platform bans political content globally"

---

*MASTER_FIX_PROMPT.md — butterfly-effect*
*Single session prompt. Read completely before writing any code.*
*Work through Sections 1-7 in order. Do not skip. Do not merge sections.*
*Section 1 fixes the root cause. Sections 2-6 fix everything else.*
*Section 7 verifies it all works.*