"""Tests for FRED ingester."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from butterfly.ingestion.fred import FREDIngester


@pytest.mark.asyncio
async def test_fred_ingester_no_api_key():
    """Test FRED ingester with no API key."""
    with patch("butterfly.ingestion.fred.settings") as mock_settings:
        mock_settings.fred_api_key = None
        ingester = FREDIngester()
        events = await ingester.ingest()
        assert events == []


@pytest.mark.asyncio
async def test_fred_ingester_with_mock_data():
    """Test FRED ingester with mocked API response."""
    mock_response = {
        "observations": [
            {"value": "5.33", "date": "2024-01-15"},
            {"value": "5.25", "date": "2024-01-08"},
        ]
    }

    with patch("butterfly.ingestion.fred.settings") as mock_settings:
        mock_settings.fred_api_key = "test_key"

        with patch("butterfly.ingestion.fred.httpx.AsyncClient") as mock_client:
            mock_get = AsyncMock()
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = AsyncMock()

            mock_client.return_value.__aenter__.return_value.get = mock_get

            with patch("butterfly.ingestion.fred.get_cache", return_value=None):
                with patch("butterfly.ingestion.fred.set_cache", new_callable=AsyncMock):
                    ingester = FREDIngester()
                    events = await ingester.ingest()

                    # Should create events for each series
                    assert len(events) > 0
                    assert all(event.source == "fred" for event in events)
