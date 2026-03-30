"""GDELT (Global Database of Events, Language, and Tone) ingester."""

import httpx
from loguru import logger
from typing import List
from datetime import datetime
import asyncio

from butterfly.ingestion.base import BaseIngester
from butterfly.models.event import EventCreate
from butterfly.db.redis import get_cache, set_cache


class GDELTIngester(BaseIngester):
    """Ingester for GDELT 2.0 Events API."""

    BASE_URL = "http://api.gdeltproject.org/api/v2/doc/doc"
    THEMES = [
        "ECON_TRADE",
        "ECON_INTEREST",
        "SUPPLY_CHAIN",
        "GEOPOLITICS",
    ]

    def __init__(self):
        """Initialize GDELT ingester."""
        super().__init__("GDELT")

    async def ingest(self) -> List[EventCreate]:
        """Fetch latest events from GDELT API.

        Returns:
            List of EventCreate objects for new events
        """
        events = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for theme in self.THEMES:
                try:
                    # Build query
                    query = f"theme:{theme}"
                    params = {
                        "query": query,
                        "mode": "artlist",
                        "format": "json",
                        "maxrecords": 250,
                    }

                    response = await client.get(self.BASE_URL, params=params)
                    response.raise_for_status()
                    data = response.json()

                    articles = data.get("articles", [])
                    logger.info(f"GDELT {theme}: fetched {len(articles)} articles")

                    # Process in batches of 50
                    for i in range(0, len(articles), 50):
                        batch = articles[i : i + 50]

                        for article in batch:
                            try:
                                url = article.get("url")
                                title = article.get("title", "")
                                date_str = article.get("seendate")
                                tone = article.get("tone", 0)
                                goldstein = article.get("goldsteinscale", 0)

                                # Skip if URL already processed
                                cache_key = f"gdelt:url:{url}"
                                if await get_cache(cache_key):
                                    continue

                                # Parse date (format: YYYYMMDDHHMMSS)
                                if date_str:
                                    try:
                                        occurred_at = datetime.strptime(
                                            date_str[:14], "%Y%m%d%H%M%S"
                                        )
                                    except ValueError:
                                        occurred_at = datetime.utcnow()
                                else:
                                    occurred_at = datetime.utcnow()

                                description = f"GDELT {theme}: {title}\nTone: {tone:.2f}, Goldstein: {goldstein:.2f}"

                                event = EventCreate(
                                    title=title[:500],  # Truncate to 500 chars
                                    description=description,
                                    source="gdelt",
                                    source_url=url,
                                    occurred_at=occurred_at,
                                    raw_text=title,
                                )
                                events.append(event)

                                # Mark URL as processed
                                await set_cache(cache_key, "1", ttl=604800)  # 7 days

                            except Exception as e:
                                logger.debug(f"Failed to process GDELT article: {e}")

                        # Delay between batches to avoid hammering the server
                        if i + 50 < len(articles):
                            await asyncio.sleep(0.1)

                except httpx.HTTPStatusError as e:
                    logger.error(f"GDELT API error for {theme}: {e}")
                except Exception as e:
                    logger.error(f"Failed to process GDELT theme {theme}: {e}")

        return events
