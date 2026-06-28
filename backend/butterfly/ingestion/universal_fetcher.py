"""
UniversalFetcher — domain-adaptive evidence fetcher.

- Sources selected by domain priority (not all sources for all domains)
- Source quality weights applied on top of keyword relevance
- Query-hash caching with 1h TTL for breaking events, 24h for historical
- Hard 6s total timeout
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx
from loguru import logger

from butterfly.logging_utils import DebugTimer, log_fetch_result

try:
    from ddgs import DDGS
    _DDGS_OK = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        _DDGS_OK = True
    except ImportError:
        _DDGS_OK = False

try:
    import feedparser
    _FEED_OK = True
except ImportError:
    _FEED_OK = False

# ── Source quality weights ────────────────────────────────────────────────────

SOURCE_QUALITY: dict[str, float] = {
    "fred":        1.00,
    "acled":       0.95,
    "openalex":    0.90,
    "reliefweb":   0.85,
    "noaa":        0.85,
    "wikipedia":   0.70,
    "rss":         0.60,
    "duckduckgo":  0.50,
    "gdelt":       0.55,
}

# ── Domain → ordered source list ─────────────────────────────────────────────

_RSS: dict[str, list[str]] = {
    "geopolitics":       ["https://feeds.bbci.co.uk/news/world/rss.xml"],
    "military":          ["https://feeds.bbci.co.uk/news/world/rss.xml"],
    "economics":         ["https://feeds.bbci.co.uk/news/business/rss.xml"],
    "financial_markets": ["https://feeds.bbci.co.uk/news/business/rss.xml"],
    "technology":        ["https://techcrunch.com/feed/"],
    "health":            ["https://feeds.bbci.co.uk/news/health/rss.xml"],
    "climate":           ["https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"],
    "energy":            ["https://feeds.bbci.co.uk/news/business/rss.xml"],
    "humanitarian":      ["https://feeds.bbci.co.uk/news/world/rss.xml"],
    "trade":             ["https://feeds.bbci.co.uk/news/business/rss.xml"],
}

_WIKI_SEARCH = "https://en.wikipedia.org/w/api.php"
_WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary"
_TOTAL_TIMEOUT = 6.0
_SOURCE_TIMEOUT = 4.0


@dataclass
class RawEvidence:
    source: str
    title: str
    content: str
    url: Optional[str] = None
    relevance_score: float = 0.5
    domain_tags: list = field(default_factory=list)

    def model_dump(self) -> dict:
        return {
            "source": self.source,
            "title": self.title[:200],
            "content": self.content[:600],
            "url": self.url,
            "relevance_score": self.relevance_score,
            "domain_tags": self.domain_tags,
        }


class UniversalFetcher:

    async def fetch(self, event) -> list[RawEvidence]:
        fetch_start = time.time()
        with DebugTimer("Universal evidence fetching"):
            queries: list[str] = getattr(event, "data_fetch_queries", [])
            if not queries:
                queries = [getattr(event, "title", str(event))]

            domains: list[str] = getattr(event, "domain", ["economics"])
            actors: list[str] = getattr(event, "primary_actors", [])
            keywords = [q[:40] for q in queries[:2]] + [a[:30] for a in actors[:2]]
            primary_domain = domains[0] if domains else "economics"

            # Cache check
            cache_key = hashlib.md5(
                f"{getattr(event, 'title', '')}:{sorted(domains)}".encode()
            ).hexdigest()
            try:
                from butterfly.db.redis import get_cache, set_cache
                cached = await get_cache(f"fetch:{cache_key}")
                if cached:
                    import json
                    items = json.loads(cached)
                    logger.info(f"💾 FETCHER Cache hit: {len(items)} items")
                    log_fetch_result("Cache", True, len(items), time.time() - fetch_start)
                    return [RawEvidence(**i) for i in items]
            except Exception:
                pass

            logger.info(f"🔍 FETCHER Starting: domain={primary_domain} queries={len(queries)}")

            # Build domain-prioritised task list
            tasks = self._build_tasks(primary_domain, domains, queries, keywords)

            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=_TOTAL_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.warning(f"⏱️  FETCHER Timeout ({_TOTAL_TIMEOUT}s)")
                results = []

            merged: list[RawEvidence] = []
            seen: set[str] = set()
            for batch in results:
                if isinstance(batch, Exception):
                    continue
                for item in (batch or []):
                    key = item.title[:80]
                    if key not in seen:
                        seen.add(key)
                        merged.append(item)

            # Score: keyword overlap × source quality weight
            kw_lower = [q.lower()[:20] for q in queries[:2]]
            for item in merged:
                combined = (item.title + " " + item.content).lower()
                kw_hits = sum(1 for kw in kw_lower if kw in combined)
                quality = SOURCE_QUALITY.get(item.source, 0.5)
                item.relevance_score = min(1.0, (item.relevance_score + kw_hits * 0.05) * quality)

            merged.sort(key=lambda r: r.relevance_score, reverse=True)
            final = merged[:30]
            logger.info(f"📊 FETCHER {len(merged)} raw → {len(final)} ranked (relevance-sorted)")

            # Cache result
            try:
                import json
                # 1h TTL for breaking events (high severity), 24h for others
                severity = getattr(event, "severity", "moderate")
                ttl = 3600 if severity in ("major", "catastrophic") else 86400
                await set_cache(f"fetch:{cache_key}", json.dumps([i.model_dump() for i in final]), ttl=ttl)
            except Exception:
                pass

            fetch_elapsed = time.time() - fetch_start
            log_fetch_result("UniversalFetcher", len(final) > 0, len(final), fetch_elapsed)
            return final

    def _build_tasks(
        self,
        primary_domain: str,
        all_domains: list[str],
        queries: list[str],
        keywords: list[str],
    ) -> list:
        """Select sources by domain priority — don't fetch ACLED for tech events."""
        tasks = []

        # Always: DDG + Wikipedia (fast, general)
        tasks.append(self._ddg(queries[:1]))
        tasks.append(self._wikipedia(queries[:1]))

        # Domain-specific sources
        if primary_domain in ("economics", "financial_markets", "trade"):
            tasks.append(self._rss_concurrent(["economics", "financial_markets"], keywords))
            tasks.append(self._world_bank(queries[:1]))

        elif primary_domain in ("geopolitics", "military"):
            tasks.append(self._rss_concurrent(["geopolitics", "military"], keywords))
            tasks.append(self._reliefweb(queries[:1]))

        elif primary_domain == "technology":
            tasks.append(self._rss_concurrent(["technology"], keywords))
            tasks.append(self._arxiv(queries[:1], categories=["cs", "econ"]))

        elif primary_domain == "health":
            tasks.append(self._rss_concurrent(["health"], keywords))
            tasks.append(self._reliefweb(queries[:1]))
            tasks.append(self._openalex(queries[:1], domain="health"))

        elif primary_domain == "climate":
            tasks.append(self._rss_concurrent(["climate"], keywords))
            tasks.append(self._noaa(queries[:1]))
            tasks.append(self._arxiv(queries[:1], categories=["physics.ao-ph", "eess.SP"]))

        elif primary_domain == "humanitarian":
            tasks.append(self._reliefweb(queries[:1]))
            tasks.append(self._rss_concurrent(["humanitarian"], keywords))

        else:
            # Fallback: RSS for detected domains
            tasks.append(self._rss_concurrent(all_domains[:2], keywords))

        return tasks

    # ── Sources ───────────────────────────────────────────────────────────────

    async def _empty(self) -> list:
        return []

    async def _ddg(self, queries: list[str]) -> list[RawEvidence]:
        if not _DDGS_OK or not queries:
            return []
        loop = asyncio.get_event_loop()

        def _search(q: str) -> list[dict]:
            try:
                with DDGS() as ddgs:
                    return list(ddgs.text(q, max_results=5))
            except Exception:
                return []

        try:
            raw = await asyncio.wait_for(
                loop.run_in_executor(None, _search, queries[0]),
                timeout=_SOURCE_TIMEOUT,
            )
            results = [RawEvidence(source="duckduckgo", title=r.get("title", ""),
                                   content=r.get("body", ""), url=r.get("href"),
                                   relevance_score=0.50) for r in raw]
            logger.info(f"[DDG] {len(results)}")
            return results
        except Exception:
            return []

    async def _wikipedia(self, queries: list[str]) -> list[RawEvidence]:
        if not queries:
            return []
        try:
            async with httpx.AsyncClient(timeout=_SOURCE_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(_WIKI_SEARCH, params={
                    "action": "query", "list": "search",
                    "srsearch": queries[0][:50], "format": "json", "srlimit": 1, "utf8": 1,
                }, headers={"Accept": "application/json"})
                if resp.status_code != 200:
                    return []
                pages = resp.json().get("query", {}).get("search", [])
                if not pages:
                    return []
                title = pages[0]["title"].replace(" ", "_")
                r2 = await client.get(f"{_WIKI_SUMMARY}/{title}", headers={"Accept": "application/json"})
                if r2.status_code == 200:
                    d = r2.json()
                    extract = d.get("extract", "")
                    if len(extract) > 80:
                        logger.info("[WIKI] 1 page")
                        return [RawEvidence(source="wikipedia", title=d.get("title", title),
                                            content=extract[:600],
                                            url=d.get("content_urls", {}).get("desktop", {}).get("page"),
                                            relevance_score=0.70)]
        except Exception:
            pass
        return []

    async def _rss_concurrent(self, domains: list[str], keywords: list[str]) -> list[RawEvidence]:
        if not _FEED_OK:
            return []
        feed_urls: list[str] = []
        for d in domains[:2]:
            feed_urls.extend(_RSS.get(d, []))
        feed_urls = list(dict.fromkeys(feed_urls))[:3]
        if not feed_urls:
            return []

        loop = asyncio.get_event_loop()
        kw_lower = [k.lower()[:20] for k in keywords if k]

        def _parse(url: str) -> list:
            try:
                return feedparser.parse(url).entries[:5]
            except Exception:
                return []

        try:
            batches = await asyncio.gather(
                *[asyncio.wait_for(loop.run_in_executor(None, _parse, u), timeout=3.0)
                  for u in feed_urls],
                return_exceptions=True,
            )
        except Exception:
            return []

        results = []
        for batch in batches:
            if isinstance(batch, Exception):
                continue
            for entry in (batch or []):
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                combined = (title + " " + summary).lower()
                if not kw_lower or any(kw in combined for kw in kw_lower):
                    results.append(RawEvidence(source="rss", title=title, content=summary,
                                               url=entry.get("link"), relevance_score=0.60))
        logger.info(f"[RSS] {len(results)}")
        return results

    async def _reliefweb(self, queries: list[str]) -> list[RawEvidence]:
        if not queries:
            return []
        try:
            async with httpx.AsyncClient(timeout=_SOURCE_TIMEOUT) as client:
                resp = await client.post("https://api.reliefweb.int/v1/reports", json={
                    "query": {"value": queries[0], "operator": "AND"},
                    "fields": {"include": ["title", "body", "url"]},
                    "limit": 4, "sort": ["date:desc"],
                })
                results = []
                for item in resp.json().get("data", []):
                    f = item.get("fields", {})
                    results.append(RawEvidence(source="reliefweb", title=f.get("title", ""),
                                               content=f.get("body", "")[:500], url=f.get("url"),
                                               relevance_score=0.85, domain_tags=["humanitarian"]))
                logger.info(f"[RELIEFWEB] {len(results)}")
                return results
        except Exception:
            return []

    async def _world_bank(self, queries: list[str]) -> list[RawEvidence]:
        """World Bank indicators API — free, no key."""
        if not queries:
            return []
        try:
            async with httpx.AsyncClient(timeout=_SOURCE_TIMEOUT) as client:
                resp = await client.get(
                    "https://search.worldbank.org/api/v2/wds",
                    params={"q": queries[0][:80], "format": "json", "rows": 3,
                            "fl": "docdt,display_title,url,abstract"},
                )
                results = []
                for doc in resp.json().get("documents", {}).values():
                    if isinstance(doc, dict) and doc.get("display_title"):
                        results.append(RawEvidence(
                            source="world_bank",
                            title=doc.get("display_title", ""),
                            content=doc.get("abstract", "")[:400],
                            url=doc.get("url"),
                            relevance_score=0.80,
                        ))
                logger.info(f"[WORLDBANK] {len(results)}")
                return results
        except Exception:
            return []

    async def _arxiv(self, queries: list[str], categories: list[str] | None = None) -> list[RawEvidence]:
        """arXiv API — free, no key. For technology and climate domains."""
        if not queries:
            return []
        try:
            cat_filter = " OR ".join(f"cat:{c}" for c in (categories or ["cs"]))
            query = f"({queries[0][:60]}) AND ({cat_filter})"
            async with httpx.AsyncClient(timeout=_SOURCE_TIMEOUT) as client:
                resp = await client.get(
                    "https://export.arxiv.org/api/query",
                    params={"search_query": query, "max_results": 3, "sortBy": "relevance"},
                )
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                results = []
                for entry in root.findall("atom:entry", ns)[:3]:
                    title = (entry.findtext("atom:title", "", ns) or "").strip()
                    summary = (entry.findtext("atom:summary", "", ns) or "").strip()
                    link = entry.findtext("atom:id", "", ns) or ""
                    if title:
                        results.append(RawEvidence(source="arxiv", title=title,
                                                   content=summary[:400], url=link,
                                                   relevance_score=0.85))
                logger.info(f"[ARXIV] {len(results)}")
                return results
        except Exception:
            return []

    async def _openalex(self, queries: list[str], domain: str = "") -> list[RawEvidence]:
        """OpenAlex — free academic works API, no key required."""
        if not queries:
            return []
        try:
            async with httpx.AsyncClient(timeout=_SOURCE_TIMEOUT) as client:
                resp = await client.get(
                    "https://api.openalex.org/works",
                    params={"search": queries[0][:80], "per-page": 3,
                            "select": "title,abstract_inverted_index,doi,publication_year"},
                    headers={"User-Agent": "butterfly-effect/1.0 (mailto:research@butterfly.app)"},
                )
                results = []
                for work in resp.json().get("results", [])[:3]:
                    title = work.get("title", "") or ""
                    # OpenAlex stores abstract as inverted index — reconstruct
                    inv = work.get("abstract_inverted_index") or {}
                    if inv:
                        words = sorted(((pos, w) for w, positions in inv.items() for pos in positions))
                        abstract = " ".join(w for _, w in words[:80])
                    else:
                        abstract = ""
                    doi = work.get("doi", "") or ""
                    if title:
                        results.append(RawEvidence(source="openalex", title=title[:200],
                                                   content=abstract[:400],
                                                   url=f"https://doi.org/{doi}" if doi else None,
                                                   relevance_score=0.90))
                logger.info(f"[OPENALEX] {len(results)}")
                return results
        except Exception:
            return []

    async def _noaa(self, queries: list[str]) -> list[RawEvidence]:
        """NOAA Climate Data Online — free, no key for basic queries."""
        if not queries:
            return []
        try:
            async with httpx.AsyncClient(timeout=_SOURCE_TIMEOUT) as client:
                # NOAA global summary search
                resp = await client.get(
                    "https://www.ncei.noaa.gov/cdo-web/api/v2/data",
                    params={"datasetid": "GHCND", "limit": 3,
                            "stationid": "GHCND:USW00094728"},  # NYC as proxy
                    headers={"token": ""},  # public endpoint, no token needed for metadata
                )
                # NOAA CDO requires token for data; use their free climate reports instead
                resp2 = await client.get(
                    "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/global/time-series/globe/land_ocean/ytd/12/1850-2024.json"
                )
                if resp2.status_code == 200:
                    data = resp2.json()
                    desc = data.get("description", {})
                    title = desc.get("title", "NOAA Global Temperature Data")
                    logger.info("[NOAA] 1 dataset")
                    return [RawEvidence(source="noaa", title=title,
                                       content=f"NOAA global climate monitoring data. {desc.get('base_period', '')}",
                                       url="https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/",
                                       relevance_score=0.85, domain_tags=["climate"])]
        except Exception:
            pass
        return []
