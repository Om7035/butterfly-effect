"""
UniversalFetcher — domain-aware evidence fetcher using all available free sources.

Sources (all free, no key unless noted):
  wikipedia     → python `wikipedia` lib — clean text, no key, no rate limit
  duckduckgo    → `duckduckgo-search` lib — live web search, no key
  gdelt         → free REST API, no key
  fred          → free, needs FRED_API_KEY
  reliefweb     → free REST API, no key (humanitarian)
  acled         → free, needs ACLED_EMAIL + ACLED_PASSWORD (OAuth2 auto-handled)
  open_meteo    → free REST API, no key (weather/climate)
  world_bank    → free REST API, no key (development indicators)
  news_api      → paid, needs NEWS_API_KEY (optional)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import datetime

import httpx
from loguru import logger
from pydantic import BaseModel

from butterfly.config import settings
from butterfly.db.redis import get_cache, set_cache
from butterfly.llm.event_parser import UniversalEvent

_TIMEOUT = httpx.Timeout(5.0)


# ── RawEvidence ───────────────────────────────────────────────────────────────

class RawEvidence(BaseModel):
    source:          str
    title:           str
    content:         str
    url:             str | None  = None
    published_at:    datetime | None = None
    relevance_score: float = 0.5
    domain_tags:     list[str] = []


# ── Wikipedia (python library — clean text, no key, no rate limit) ────────────

async def fetch_wikipedia(queries: list[str]) -> list[RawEvidence]:
    """Fetch Wikipedia summaries using the official python library."""
    results: list[RawEvidence] = []
    try:
        import wikipedia as wiki
        wiki.set_lang("en")
    except ImportError:
        logger.debug("wikipedia package not installed, skipping")
        return results

    loop = asyncio.get_event_loop()

    async def _fetch_one(q: str) -> RawEvidence | None:
        try:
            def _call():
                try:
                    page = wiki.page(q, auto_suggest=True)
                    return page.title, page.summary[:600], page.url
                except wiki.DisambiguationError as e:
                    # Take first option
                    page = wiki.page(e.options[0])
                    return page.title, page.summary[:600], page.url
                except wiki.PageError:
                    return None, None, None

            title, summary, url = await loop.run_in_executor(None, _call)
            if title and summary:
                return RawEvidence(
                    source="wikipedia",
                    title=title,
                    content=summary,
                    url=url,
                    domain_tags=["general"],
                )
        except Exception as e:
            logger.debug(f"Wikipedia fetch failed for '{q}': {e}")
        return None

    tasks = [_fetch_one(q) for q in queries[:5]]
    for result in await asyncio.gather(*tasks, return_exceptions=True):
        if isinstance(result, RawEvidence):
            results.append(result)

    return results


# ── DuckDuckGo (zero setup, no key, live web search) ─────────────────────────

async def fetch_duckduckgo(queries: list[str]) -> list[RawEvidence]:
    """Fetch live web search results via DuckDuckGo (no API key needed)."""
    results: list[RawEvidence] = []
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.debug("duckduckgo-search not installed, skipping")
        return results

    loop = asyncio.get_event_loop()

    for q in queries[:3]:
        try:
            def _search(query=q):
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=5))

            hits = await loop.run_in_executor(None, _search)
            for hit in hits:
                results.append(RawEvidence(
                    source="duckduckgo",
                    title=hit.get("title", "")[:200],
                    content=hit.get("body", "")[:500],
                    url=hit.get("href"),
                    domain_tags=["news", "general"],
                ))
        except Exception as e:
            logger.debug(f"DuckDuckGo search failed for '{q}': {e}")

    return results


# ── FRED (free, needs FRED_API_KEY) ──────────────────────────────────────────

async def fetch_fred(queries: list[str]) -> list[RawEvidence]:
    """Fetch FRED economic series observations."""
    if not settings.fred_api_key:
        return []
    results: list[RawEvidence] = []
    series_map = {
        "oil": "DCOILWTICO", "crude": "DCOILWTICO",
        "mortgage": "MORTGAGE30US", "housing": "HOUST",
        "unemployment": "UNRATE", "inflation": "CPIAUCSL",
        "fed": "FEDFUNDS", "rate": "FEDFUNDS", "fomc": "FEDFUNDS",
        "gdp": "GDP", "yield": "T10Y2Y", "treasury": "T10Y2Y",
        "gas": "GASREGCOVW", "natural gas": "MHHNGSP",
        "dollar": "DTWEXBGS", "vix": "VIXCLS", "sp500": "SP500",
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
                            params={"series_id": series_id, "api_key": settings.fred_api_key,
                                    "limit": 5, "sort_order": "desc", "file_type": "json"},
                        )
                        if r.status_code == 200:
                            obs = r.json().get("observations", [])
                            if obs:
                                latest = obs[0]
                                results.append(RawEvidence(
                                    source="fred",
                                    title=f"FRED {series_id}: {latest.get('value')}",
                                    content=f"FRED series {series_id} latest: {latest.get('value')} on {latest.get('date')}",
                                    url=f"https://fred.stlouisfed.org/series/{series_id}",
                                    published_at=datetime.fromisoformat(latest["date"]) if latest.get("date") else None,
                                    domain_tags=["economics", "financial_markets"],
                                ))
                    except Exception as e:
                        logger.debug(f"FRED fetch failed for {series_id}: {e}")
    return results


# ── GDELT (free, no key) ──────────────────────────────────────────────────────

async def fetch_gdelt(queries: list[str]) -> list[RawEvidence]:
    """Fetch GDELT article list."""
    results: list[RawEvidence] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(4.0)) as client:
        for q in queries[:1]:
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


# ── ACLED (free, OAuth2 auto-handled) ─────────────────────────────────────────

_acled_token: str | None = None
_acled_token_expiry: float = 0.0


async def _get_acled_token() -> str | None:
    """Get ACLED OAuth2 access token, auto-refreshing when expired."""
    global _acled_token, _acled_token_expiry

    if not settings.acled_email or not settings.acled_password:
        return None

    if _acled_token and time.time() < _acled_token_expiry:
        return _acled_token

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                "https://acleddata.com/user/login?_format=json",
                json={"name": settings.acled_email, "pass": settings.acled_password},
                headers={"Content-Type": "application/json"},
            )
            if r.status_code == 200:
                data = r.json()
                _acled_token = data.get("access_token") or data.get("current_user", {}).get("access_token")
                # Token valid 24h; refresh 1h early
                _acled_token_expiry = time.time() + 23 * 3600
                logger.info("ACLED token obtained")
                return _acled_token
    except Exception as e:
        logger.debug(f"ACLED auth failed: {e}")
    return None


async def fetch_acled(queries: list[str]) -> list[RawEvidence]:
    """Fetch ACLED armed conflict data (OAuth2 auto-handled)."""
    token = await _get_acled_token()
    if not token:
        return []

    results: list[RawEvidence] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for _q in queries[:2]:
            try:
                r = await client.get(
                    "https://api.acleddata.com/acled/read",
                    params={"terms": "accept", "event_type": "Battles", "limit": 5},
                    headers={"Authorization": f"Bearer {token}"},
                )
                if r.status_code == 200:
                    for ev in r.json().get("data", [])[:5]:
                        results.append(RawEvidence(
                            source="acled",
                            title=f"ACLED: {ev.get('event_type', '')} in {ev.get('country', '')}",
                            content=str(ev.get("notes", ""))[:500],
                            url="https://acleddata.com",
                            domain_tags=["military", "geopolitics"],
                        ))
            except Exception as e:
                logger.debug(f"ACLED fetch failed: {e}")
    return results


# ── ReliefWeb (free, no key) ──────────────────────────────────────────────────

async def fetch_reliefweb(queries: list[str]) -> list[RawEvidence]:
    """Fetch ReliefWeb humanitarian reports."""
    results: list[RawEvidence] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for q in queries[:2]:
            try:
                r = await client.post(
                    "https://api.reliefweb.int/v1/reports",
                    json={"query": {"value": q},
                          "fields": {"include": ["title", "body-html", "url", "date"]},
                          "limit": 5},
                    headers={"User-Agent": "butterfly-effect/0.4"},
                )
                if r.status_code == 200:
                    import re
                    for item in r.json().get("data", [])[:5]:
                        fields = item.get("fields", {})
                        body = re.sub(r"<[^>]+>", " ", fields.get("body-html", ""))[:500]
                        results.append(RawEvidence(
                            source="reliefweb",
                            title=fields.get("title", "")[:200],
                            content=body,
                            url=fields.get("url"),
                            domain_tags=["humanitarian", "geopolitics"],
                        ))
            except Exception as e:
                logger.debug(f"ReliefWeb fetch failed for '{q}': {e}")
    return results


# ── Open-Meteo (free, no key) ─────────────────────────────────────────────────

async def fetch_open_meteo(queries: list[str]) -> list[RawEvidence]:
    """Fetch Open-Meteo weather/climate data."""
    results: list[RawEvidence] = []
    location_map = {
        "florida": (25.76, -80.19), "miami": (25.76, -80.19),
        "texas": (31.97, -99.90), "california": (36.78, -119.42),
        "japan": (35.68, 139.65), "india": (20.59, 78.96),
        "europe": (54.53, 15.26), "middle east": (29.31, 47.48),
        "gulf": (26.07, 50.56), "ukraine": (48.38, 31.17),
        "china": (35.86, 104.20), "australia": (-25.27, 133.78),
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for q in queries[:2]:
            q_lower = q.lower()
            lat, lon = next(((v) for k, v in location_map.items() if k in q_lower), (None, None))
            if lat is None:
                continue
            try:
                r = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={"latitude": lat, "longitude": lon,
                            "daily": "temperature_2m_max,precipitation_sum,windspeed_10m_max",
                            "forecast_days": 7, "timezone": "auto"},
                )
                if r.status_code == 200:
                    d = r.json().get("daily", {})
                    results.append(RawEvidence(
                        source="open_meteo",
                        title=f"Weather forecast for {q}",
                        content=f"7-day: max temps {d.get('temperature_2m_max', [])[:3]}°C, "
                                f"precip {d.get('precipitation_sum', [])[:3]}mm",
                        url="https://open-meteo.com",
                        domain_tags=["climate", "environment"],
                    ))
            except Exception as e:
                logger.debug(f"Open-Meteo fetch failed: {e}")
    return results


# ── World Bank (free, no key) ─────────────────────────────────────────────────

async def fetch_world_bank(queries: list[str]) -> list[RawEvidence]:
    """Fetch World Bank development indicators."""
    results: list[RawEvidence] = []
    indicator_map = {
        "gdp": "NY.GDP.MKTP.CD", "inflation": "FP.CPI.TOTL.ZG",
        "unemployment": "SL.UEM.TOTL.ZS", "poverty": "SI.POV.DDAY",
        "trade": "NE.TRD.GNFS.ZS", "oil": "NY.GDP.PETR.RT.ZS",
        "food": "SN.ITK.DEFC.ZS", "debt": "GC.DOD.TOTL.GD.ZS",
    }
    country_map = {
        "israel": "ISR", "iran": "IRN", "russia": "RUS", "china": "CHN",
        "usa": "USA", "ukraine": "UKR", "india": "IND", "brazil": "BRA",
        "japan": "JPN", "germany": "DEU", "france": "FRA", "uk": "GBR",
        "saudi": "SAU", "turkey": "TUR",
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
                                    content=f"{entry.get('indicator', {}).get('value', indicator)}: "
                                            f"{entry.get('value')} ({entry.get('date')})",
                                    url=f"https://data.worldbank.org/indicator/{indicator}?locations={country}",
                                    domain_tags=["economics", "development"],
                                ))
            except Exception as e:
                logger.debug(f"World Bank fetch failed: {e}")
    return results


# ── NewsAPI (paid, optional) ──────────────────────────────────────────────────

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
                            domain_tags=["news"],
                        ))
            except Exception as e:
                logger.debug(f"NewsAPI fetch failed: {e}")
    return results


# ── Domain → fetcher routing ──────────────────────────────────────────────────

DOMAIN_FETCHER_MAP: dict[str, list] = {
    "geopolitics":       [fetch_duckduckgo, fetch_gdelt, fetch_reliefweb, fetch_acled, fetch_wikipedia],
    "military":          [fetch_acled, fetch_gdelt, fetch_duckduckgo, fetch_wikipedia],
    "economics":         [fetch_fred, fetch_world_bank, fetch_duckduckgo, fetch_wikipedia],
    "financial_markets": [fetch_fred, fetch_duckduckgo, fetch_wikipedia, fetch_world_bank],
    "energy":            [fetch_fred, fetch_duckduckgo, fetch_gdelt, fetch_wikipedia],
    "climate":           [fetch_open_meteo, fetch_duckduckgo, fetch_wikipedia, fetch_reliefweb],
    "environment":       [fetch_open_meteo, fetch_duckduckgo, fetch_wikipedia],
    "technology":        [fetch_duckduckgo, fetch_wikipedia],
    "health":            [fetch_reliefweb, fetch_duckduckgo, fetch_wikipedia],
    "humanitarian":      [fetch_reliefweb, fetch_acled, fetch_duckduckgo, fetch_world_bank],
    "logistics":         [fetch_duckduckgo, fetch_wikipedia, fetch_world_bank],
    "trade":             [fetch_fred, fetch_world_bank, fetch_duckduckgo, fetch_wikipedia],
    "political":         [fetch_duckduckgo, fetch_gdelt, fetch_wikipedia],
    "social":            [fetch_duckduckgo, fetch_wikipedia],
    "cultural":          [fetch_duckduckgo, fetch_wikipedia],
}

_DEFAULT_FETCHERS = [fetch_duckduckgo, fetch_wikipedia]


# ── UniversalFetcher ──────────────────────────────────────────────────────────

class UniversalFetcher:
    """Fetch real-world evidence for any event, routed by domain."""

    async def fetch(self, event: UniversalEvent) -> list[RawEvidence]:
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

        fetcher_set: set = set()
        for domain in event.domain:
            for fn in DOMAIN_FETCHER_MAP.get(domain, _DEFAULT_FETCHERS):
                fetcher_set.add(fn)
        if not fetcher_set:
            fetcher_set = set(_DEFAULT_FETCHERS)

        logger.info(f"Fetching evidence: {len(fetcher_set)} sources for domains {event.domain}")

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

        # Score relevance
        actors_lower = [a.lower() for a in event.primary_actors]
        for item in unique:
            content_lower = (item.title + " " + item.content).lower()
            hits = sum(1 for a in actors_lower if a in content_lower)
            item.relevance_score = min(1.0, 0.3 + hits * 0.2)

        unique.sort(key=lambda x: x.relevance_score, reverse=True)
        final = unique[:50]

        await set_cache(cache_key, json.dumps([r.model_dump(mode="json") for r in final]), ttl=21600)
        logger.info(f"Fetched {len(final)} evidence items for '{event.title}'")
        return final
