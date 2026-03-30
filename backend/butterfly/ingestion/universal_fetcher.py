"""
UniversalFetcher — domain-aware data fetcher that assembles evidence
for ANY event type using free public APIs.

Sources:
  wikipedia   → free, no key
  gdelt       → free, no key
  fred        → free, needs FRED_API_KEY
  reliefweb   → free, no key (humanitarian)
  acled       → free, needs ACLED_API_KEY (armed conflict)
  open_meteo  → free, no key (weather/climate)
  world_bank  → free, no key (development indicators)
  news_api    → $50/mo, needs NEWS_API_KEY (optional)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Callable, Optional

import httpx
from loguru import logger
from pydantic import BaseModel

from butterfly.config import settings
from butterfly.db.redis import get_cache, set_cache
from butterfly.llm.event_parser import UniversalEvent

# ── RawEvidence ───────────────────────────────────────────────────────────────

class RawEvidence(BaseModel):
    source:          str
    title:           str
    content:         str            # max 500 chars
    url:             Optional[str]  = None
    published_at:    Optional[datetime] = None
    relevance_score: float          = 0.5
    domain_tags:     list[str]      = []


# ── Individual fetchers ───────────────────────────────────────────────────────

_TIMEOUT = httpx.Timeout(10.0)


async def fetch_wikipedia(queries: list[str]) -> list[RawEvidence]:
    """Fetch Wikipedia article summaries for each query."""
    results: list[RawEvidence] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for q in queries[:4]:
            try:
                title = q.replace(" ", "_")
                r = await client.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                    headers={"User-Agent": "butterfly-effect/0.4 (causal-inference-engine)"},
                )
                if r.status_code == 200:
                    d = r.json()
                    results.append(RawEvidence(
                        source="wikipedia",
                        title=d.get("title", q),
                        content=d.get("extract", "")[:500],
                        url=d.get("content_urls", {}).get("desktop", {}).get("page"),
                        domain_tags=["general"],
                    ))
            except Exception as e:
                logger.debug(f"Wikipedia fetch failed for '{q}': {e}")
    return results


async def fetch_gdelt(queries: list[str]) -> list[RawEvidence]:
    """Fetch GDELT article list for each query."""
    results: list[RawEvidence] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for q in queries[:3]:
            try:
                r = await client.get(
                    "http://api.gdeltproject.org/api/v2/doc/doc",
                    params={"query": q, "mode": "artlist", "format": "json", "maxrecords": 10},
                )
                if r.status_code == 200:
                    for art in r.json().get("articles", [])[:5]:
                        results.append(RawEvidence(
                            source="gdelt",
                            title=art.get("title", "")[:200],
                            content=art.get("title", "")[:500],
                            url=art.get("url"),
                            domain_tags=["geopolitics", "news"],
                        ))
            except Exception as e:
                logger.debug(f"GDELT fetch failed for '{q}': {e}")
    return results


async def fetch_fred(queries: list[str]) -> list[RawEvidence]:
    """Fetch FRED economic series observations."""
    if not settings.fred_api_key:
        return []
    results: list[RawEvidence] = []
    # Map common query terms to FRED series IDs
    series_map = {
        "oil": "DCOILWTICO", "crude": "DCOILWTICO",
        "mortgage": "MORTGAGE30US", "housing": "HOUST",
        "unemployment": "UNRATE", "inflation": "CPIAUCSL",
        "fed": "FEDFUNDS", "rate": "FEDFUNDS",
        "gdp": "GDP", "yield": "T10Y2Y",
        "gas": "GASREGCOVW", "natural gas": "MHHNGSP",
    }
    seen: set[str] = set()
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for q in queries:
            q_lower = q.lower()
            for kw, series_id in series_map.items():
                if kw in q_lower and series_id not in seen:
                    seen.add(series_id)
                    try:
                        r = await client.get(
                            "https://api.stlouisfed.org/fred/series/observations",
                            params={
                                "series_id": series_id,
                                "api_key": settings.fred_api_key,
                                "limit": 5,
                                "sort_order": "desc",
                                "file_type": "json",
                            },
                        )
                        if r.status_code == 200:
                            obs = r.json().get("observations", [])
                            if obs:
                                latest = obs[0]
                                results.append(RawEvidence(
                                    source="fred",
                                    title=f"FRED {series_id}: {latest.get('value')}",
                                    content=f"FRED series {series_id} latest value: {latest.get('value')} on {latest.get('date')}",
                                    url=f"https://fred.stlouisfed.org/series/{series_id}",
                                    published_at=datetime.fromisoformat(latest["date"]) if latest.get("date") else None,
                                    domain_tags=["economics", "financial_markets"],
                                ))
                    except Exception as e:
                        logger.debug(f"FRED fetch failed for {series_id}: {e}")
    return results


async def fetch_reliefweb(queries: list[str]) -> list[RawEvidence]:
    """Fetch ReliefWeb humanitarian reports."""
    results: list[RawEvidence] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for q in queries[:2]:
            try:
                r = await client.post(
                    "https://api.reliefweb.int/v1/reports",
                    json={
                        "query": {"value": q},
                        "fields": {"include": ["title", "body-html", "url", "date"]},
                        "limit": 5,
                    },
                    headers={"User-Agent": "butterfly-effect/0.4"},
                )
                if r.status_code == 200:
                    for item in r.json().get("data", [])[:5]:
                        fields = item.get("fields", {})
                        body = fields.get("body-html", "")
                        # Strip HTML tags
                        import re
                        body_clean = re.sub(r"<[^>]+>", " ", body)[:500]
                        results.append(RawEvidence(
                            source="reliefweb",
                            title=fields.get("title", "")[:200],
                            content=body_clean,
                            url=fields.get("url"),
                            domain_tags=["humanitarian", "geopolitics"],
                        ))
            except Exception as e:
                logger.debug(f"ReliefWeb fetch failed for '{q}': {e}")
    return results


async def fetch_acled(queries: list[str]) -> list[RawEvidence]:
    """Fetch ACLED armed conflict data (requires free API key)."""
    if not settings.acled_api_key:
        return []
    results: list[RawEvidence] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for q in queries[:2]:
            try:
                r = await client.get(
                    "https://api.acleddata.com/acled/read",
                    params={
                        "key": settings.acled_api_key,
                        "email": "research@butterfly-effect.dev",
                        "terms": "accept",
                        "event_type": "Battles",
                        "limit": 5,
                    },
                )
                if r.status_code == 200:
                    for ev in r.json().get("data", [])[:5]:
                        results.append(RawEvidence(
                            source="acled",
                            title=f"ACLED: {ev.get('event_type', '')} in {ev.get('country', '')}",
                            content=f"{ev.get('notes', '')}".strip()[:500],
                            url="https://acleddata.com",
                            domain_tags=["military", "geopolitics"],
                        ))
            except Exception as e:
                logger.debug(f"ACLED fetch failed: {e}")
    return results


async def fetch_open_meteo(queries: list[str]) -> list[RawEvidence]:
    """Fetch Open-Meteo weather/climate data (free, no key)."""
    results: list[RawEvidence] = []
    # Extract location hints from queries
    location_map = {
        "florida": (25.7617, -80.1918), "miami": (25.7617, -80.1918),
        "texas": (31.9686, -99.9018), "california": (36.7783, -119.4179),
        "japan": (35.6762, 139.6503), "tokyo": (35.6762, 139.6503),
        "india": (20.5937, 78.9629), "europe": (54.5260, 15.2551),
        "middle east": (29.3117, 47.4818), "gulf": (26.0667, 50.5577),
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for q in queries[:2]:
            q_lower = q.lower()
            lat, lon = 0.0, 0.0
            for loc, coords in location_map.items():
                if loc in q_lower:
                    lat, lon = coords
                    break
            if lat == 0.0:
                continue
            try:
                r = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat, "longitude": lon,
                        "daily": "temperature_2m_max,precipitation_sum,windspeed_10m_max",
                        "forecast_days": 7,
                        "timezone": "auto",
                    },
                )
                if r.status_code == 200:
                    d = r.json()
                    daily = d.get("daily", {})
                    temps = daily.get("temperature_2m_max", [])
                    precip = daily.get("precipitation_sum", [])
                    results.append(RawEvidence(
                        source="open_meteo",
                        title=f"Weather forecast for {q}",
                        content=f"7-day forecast: max temps {temps[:3]}, precipitation {precip[:3]} mm",
                        url="https://open-meteo.com",
                        domain_tags=["climate", "environment"],
                    ))
            except Exception as e:
                logger.debug(f"Open-Meteo fetch failed: {e}")
    return results


async def fetch_world_bank(queries: list[str]) -> list[RawEvidence]:
    """Fetch World Bank development indicators."""
    results: list[RawEvidence] = []
    # Map query terms to World Bank indicator codes
    indicator_map = {
        "gdp": "NY.GDP.MKTP.CD",
        "inflation": "FP.CPI.TOTL.ZG",
        "unemployment": "SL.UEM.TOTL.ZS",
        "poverty": "SI.POV.DDAY",
        "trade": "NE.TRD.GNFS.ZS",
        "oil": "NY.GDP.PETR.RT.ZS",
        "food": "SN.ITK.DEFC.ZS",
    }
    country_map = {
        "israel": "ISR", "iran": "IRN", "russia": "RUS", "china": "CHN",
        "usa": "USA", "ukraine": "UKR", "turkey": "TUR", "india": "IND",
        "brazil": "BRA", "japan": "JPN", "germany": "DEU", "france": "FRA",
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for q in queries[:2]:
            q_lower = q.lower()
            indicator = next((v for k, v in indicator_map.items() if k in q_lower), "NY.GDP.MKTP.CD")
            country = next((v for k, v in country_map.items() if k in q_lower), "WLD")
            try:
                r = await client.get(
                    f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}",
                    params={"format": "json", "mrv": 3, "per_page": 3},
                )
                if r.status_code == 200:
                    data = r.json()
                    if len(data) > 1 and data[1]:
                        for entry in data[1][:2]:
                            if entry.get("value"):
                                results.append(RawEvidence(
                                    source="world_bank",
                                    title=f"World Bank {indicator} for {country}",
                                    content=f"{entry.get('indicator', {}).get('value', indicator)}: {entry.get('value')} ({entry.get('date')})",
                                    url=f"https://data.worldbank.org/indicator/{indicator}?locations={country}",
                                    domain_tags=["economics", "development"],
                                ))
            except Exception as e:
                logger.debug(f"World Bank fetch failed: {e}")
    return results


async def fetch_news_api(queries: list[str]) -> list[RawEvidence]:
    """Fetch NewsAPI articles (requires paid key — graceful skip if absent)."""
    if not settings.news_api_key:
        return []
    results: list[RawEvidence] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for q in queries[:2]:
            try:
                r = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={"q": q, "pageSize": 5, "sortBy": "relevancy", "language": "en"},
                    headers={"X-Api-Key": settings.news_api_key},
                )
                if r.status_code == 200:
                    for art in r.json().get("articles", [])[:5]:
                        results.append(RawEvidence(
                            source="news_api",
                            title=art.get("title", "")[:200],
                            content=(art.get("description") or art.get("title", ""))[:500],
                            url=art.get("url"),
                            published_at=datetime.fromisoformat(art["publishedAt"].replace("Z", "+00:00")) if art.get("publishedAt") else None,
                            domain_tags=["news"],
                        ))
            except Exception as e:
                logger.debug(f"NewsAPI fetch failed: {e}")
    return results


# ── Domain → fetcher routing ──────────────────────────────────────────────────

FetcherFn = Callable[[list[str]], "asyncio.coroutines"]

DOMAIN_FETCHER_MAP: dict[str, list] = {
    "geopolitics":       [fetch_gdelt, fetch_reliefweb, fetch_acled, fetch_wikipedia],
    "military":          [fetch_acled, fetch_gdelt, fetch_reliefweb, fetch_wikipedia],
    "economics":         [fetch_fred, fetch_world_bank, fetch_gdelt, fetch_wikipedia],
    "financial_markets": [fetch_fred, fetch_gdelt, fetch_news_api, fetch_wikipedia],
    "energy":            [fetch_fred, fetch_gdelt, fetch_wikipedia, fetch_world_bank],
    "climate":           [fetch_open_meteo, fetch_reliefweb, fetch_wikipedia, fetch_gdelt],
    "environment":       [fetch_open_meteo, fetch_wikipedia, fetch_reliefweb],
    "technology":        [fetch_wikipedia, fetch_news_api, fetch_gdelt],
    "health":            [fetch_reliefweb, fetch_wikipedia, fetch_news_api, fetch_gdelt],
    "humanitarian":      [fetch_reliefweb, fetch_gdelt, fetch_wikipedia, fetch_world_bank],
    "logistics":         [fetch_gdelt, fetch_wikipedia, fetch_world_bank],
    "trade":             [fetch_fred, fetch_world_bank, fetch_gdelt, fetch_wikipedia],
    "political":         [fetch_gdelt, fetch_reliefweb, fetch_wikipedia, fetch_news_api],
    "social":            [fetch_gdelt, fetch_wikipedia, fetch_news_api],
    "cultural":          [fetch_wikipedia, fetch_news_api, fetch_gdelt],
}

_DEFAULT_FETCHERS = [fetch_gdelt, fetch_wikipedia]


# ── UniversalFetcher ──────────────────────────────────────────────────────────

class UniversalFetcher:
    """Fetch real-world evidence for any event, routed by domain."""

    async def fetch(self, event: UniversalEvent) -> list[RawEvidence]:
        """Fetch evidence for the event. Returns up to 50 results."""
        # Cache key = hash of queries + domains
        cache_key = "evidence:" + hashlib.md5(
            json.dumps(sorted(event.data_fetch_queries) + sorted(event.domain)).encode()
        ).hexdigest()

        cached = await get_cache(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                logger.info(f"Evidence cache hit: {len(data)} items")
                return [RawEvidence(**item) for item in data]
            except Exception:
                pass

        # Determine which fetchers to call
        fetcher_set: set = set()
        for domain in event.domain:
            for fn in DOMAIN_FETCHER_MAP.get(domain, _DEFAULT_FETCHERS):
                fetcher_set.add(fn)

        if not fetcher_set:
            fetcher_set = set(_DEFAULT_FETCHERS)

        logger.info(f"Fetching evidence: {len(fetcher_set)} sources for domains {event.domain}")

        # Run all fetchers concurrently
        tasks = [fn(event.data_fetch_queries) for fn in fetcher_set]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: list[RawEvidence] = []
        for r in results_nested:
            if isinstance(r, list):
                all_results.extend(r)
            elif isinstance(r, Exception):
                logger.debug(f"Fetcher error (ignored): {r}")

        # Deduplicate by URL/title
        seen: set[str] = set()
        unique: list[RawEvidence] = []
        for item in all_results:
            key = item.url or item.title
            if key and key not in seen:
                seen.add(key)
                unique.append(item)

        # Score relevance: does content mention primary actors?
        actors_lower = [a.lower() for a in event.primary_actors]
        for item in unique:
            content_lower = (item.title + " " + item.content).lower()
            hits = sum(1 for a in actors_lower if a in content_lower)
            item.relevance_score = min(1.0, 0.3 + hits * 0.2)

        # Sort by relevance, cap at 50
        unique.sort(key=lambda x: x.relevance_score, reverse=True)
        final = unique[:50]

        # Cache for 6 hours
        await set_cache(cache_key, json.dumps([r.model_dump(mode="json") for r in final]), ttl=21600)

        logger.info(f"Fetched {len(final)} evidence items for '{event.title}'")
        return final
