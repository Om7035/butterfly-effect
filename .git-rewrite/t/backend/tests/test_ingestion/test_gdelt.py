"""Tests for GDELT ingester."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from butterfly.ingestion.gdelt import GDELTIngester


@pytest.mark.asyncio
async def test_gdelt_ingester_with_mock_data():
    """Test GDELT ingester with mocked API response."""
    mock_response = {
        "articles": [
            {
                "url": "https://example.com/article1",
                "title": "Trade tensions escalate",
                "seendate": "20240115120000",
                "tone": -5.2,
                "goldsteinscale": -3.5,
            },
            {
                "url": "https://example.com/article2",
                "title": "Supply chain disruption",
                "seendate": "20240115110000",
                "tone": -4.1,
                "goldsteinscale": -2.8,
            },
        ]
    }

    with patch("butterfly.ingestion.gdelt.httpx.AsyncClient") as mock_client:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = mock_response

        mock_get = AsyncMock(return_value=mock_resp)
        mock_client.return_value.__aenter__.return_value.get = mock_get

        with patch("butterfly.ingestion.gdelt.get_cache", new_callable=AsyncMock, return_value=None):
            with patch("butterfly.ingestion.gdelt.set_cache", new_callable=AsyncMock):
                ingester = GDELTIngester()
                events = await ingester.ingest()

                assert len(events) > 0
                assert all(event.source == "gdelt" for event in events)
                assert all(event.title for event in events)


@pytest.mark.asyncio
async def test_gdelt_ingester_deduplication():
    """Test GDELT ingester deduplicates URLs."""
    mock_response = {
        "articles": [
            {
                "url": "https://example.com/article1",
                "title": "Trade tensions",
                "seendate": "20240115120000",
                "tone": -5.2,
                "goldsteinscale": -3.5,
            },
        ]
    }

    with patch("butterfly.ingestion.gdelt.httpx.AsyncClient") as mock_client:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = mock_response

        mock_get = AsyncMock(return_value=mock_resp)
        mock_client.return_value.__aenter__.return_value.get = mock_get

        # Simulate URL already in cache
        with patch("butterfly.ingestion.gdelt.get_cache", new_callable=AsyncMock, return_value="1"):
            with patch("butterfly.ingestion.gdelt.set_cache", new_callable=AsyncMock):
                ingester = GDELTIngester()
                events = await ingester.ingest()

                assert len(events) == 0
