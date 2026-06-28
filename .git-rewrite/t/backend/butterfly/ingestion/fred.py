"""FRED (Federal Reserve Economic Data) API ingester."""

from datetime import datetime
from typing import ClassVar

import httpx
from loguru import logger

from butterfly.config import settings
from butterfly.db.redis import get_cache, set_cache
from butterfly.ingestion.base import BaseIngester
from butterfly.models.event import EventCreate


class FREDIngester(BaseIngester):
    """Ingester for FRED API data."""

    BASE_URL = "https://api.stlouisfed.org/fred"
    SERIES_IDS: ClassVar[list[str]] = [
        "FEDFUNDS",      # Fed funds rate
        "MORTGAGE30US",  # 30-year mortgage rate
        "HOUST",         # Housing starts
        "UNRATE",        # Unemployment rate
        "T10Y2Y",        # Yield curve spread
    ]

    def __init__(self):
        """Initialize FRED ingester."""
        super().__init__("FRED")
        self.api_key = settings.fred_api_key
        if not self.api_key:
            logger.warning("FRED_API_KEY not set — FRED ingestion will be skipped")

    async def ingest(self) -> list[EventCreate]:
        """Fetch latest data from FRED API.

        Returns:
            List of EventCreate objects for new data points
        """
        if not self.api_key:
            return []

        events = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for series_id in self.SERIES_IDS:
                try:
                    # Check cache first
                    cache_key = f"fred:{series_id}:last_value"
                    cached = await get_cache(cache_key)

                    # Fetch latest observation
                    url = f"{self.BASE_URL}/series/observations"
                    params = {
                        "series_id": series_id,
                        "api_key": self.api_key,
                        "limit": 2,  # Get last 2 to compare
                        "sort_order": "desc",
                    }

                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    if "observations" in data and len(data["observations"]) > 0:
                        obs = data["observations"][0]
                        value = obs.get("value")
                        date = obs.get("date")

                        # Skip if value is missing
                        if value == "." or not value:
                            continue

                        value_float = float(value)

                        # Create event if value changed
                        if cached is None or float(cached) != value_float:
                            # Get previous value for context
                            prev_value = None
                            if len(data["observations"]) > 1:
                                prev_obs = data["observations"][1]
                                prev_val = prev_obs.get("value")
                                if prev_val != ".":
                                    prev_value = float(prev_val)

                            # Calculate change
                            change_pct = 0.0
                            if prev_value is not None:
                                change_pct = ((value_float - prev_value) / prev_value) * 100

                            description = f"FRED {series_id}: {value_float}"
                            if prev_value is not None:
                                description += f" (prev: {prev_value}, change: {change_pct:+.2f}%)"

                            event = EventCreate(
                                title=f"FRED: {series_id} = {value_float}",
                                description=description,
                                source="fred",
                                source_url=f"https://fred.stlouisfed.org/series/{series_id}",
                                occurred_at=datetime.fromisoformat(date),
                                raw_text=f"Federal Reserve Economic Data: {series_id} observation",
                            )
                            events.append(event)

                            # Update cache
                            await set_cache(cache_key, str(value_float), ttl=86400)

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        logger.warning(f"FRED API rate limited for {series_id}")
                        break  # Stop processing other series
                    else:
                        logger.error(f"FRED API error for {series_id}: {e}")
                except Exception as e:
                    logger.error(f"Failed to process FRED series {series_id}: {e}")

        return events
