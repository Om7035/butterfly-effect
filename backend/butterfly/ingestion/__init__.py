"""Data ingestion modules."""

from butterfly.ingestion.base import BaseIngester
from butterfly.ingestion.fred import FREDIngester
from butterfly.ingestion.gdelt import GDELTIngester

__all__ = ["BaseIngester", "FREDIngester", "GDELTIngester"]
