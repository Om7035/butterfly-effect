"""Base ingester abstract class."""

from abc import ABC, abstractmethod
from loguru import logger
from typing import List
from datetime import datetime

from butterfly.models.event import EventCreate


class BaseIngester(ABC):
    """Abstract base class for all data ingesters."""

    def __init__(self, name: str):
        """Initialize ingester.

        Args:
            name: Name of the ingester (e.g., "FRED", "GDELT")
        """
        self.name = name
        self.last_run: datetime | None = None

    @abstractmethod
    async def ingest(self) -> List[EventCreate]:
        """Ingest data and return list of events.

        Returns:
            List of EventCreate objects ready to be stored

        Raises:
            Exception: If ingestion fails (should be caught and logged)
        """
        pass

    async def run(self) -> int:
        """Run the ingester and return count of events created.

        Returns:
            Number of new events created
        """
        try:
            logger.info(f"Starting {self.name} ingestion")
            events = await self.ingest()
            self.last_run = datetime.utcnow()
            logger.info(f"{self.name} ingestion complete: {len(events)} events")
            return len(events)
        except Exception as e:
            logger.error(f"{self.name} ingestion failed: {e}")
            return 0
