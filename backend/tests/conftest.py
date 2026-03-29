"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return {
        "event_id": "test_event_001",
        "title": "Test Event",
        "description": "A test event for unit testing",
        "source": "manual",
        "source_url": None,
        "occurred_at": "2024-01-01T12:00:00Z",
        "entities": [],
        "raw_text": "This is a test event.",
        "processed": False,
    }
