"""Tests for events API."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from butterfly.models.event import EventCreate


@pytest.mark.asyncio
async def test_create_event(sample_event_data):
    """Test creating an event via API."""
    from butterfly.api.events import create_event
    from datetime import datetime

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    # Make refresh set created_at on the ORM object
    async def mock_refresh(obj):
        obj.created_at = datetime(2024, 1, 1, 12, 0, 0)

    mock_db.refresh = mock_refresh

    event_create = EventCreate(**sample_event_data)

    with patch("butterfly.api.events.uuid.uuid4") as mock_uuid:
        mock_uuid.return_value.hex = "test123456789abc"
        result = await create_event(event_create, mock_db)

        assert result["status"] == "processing"
        assert "event_id" in result
        assert result["event_id"].startswith("event_")
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
