"""Event data models for Pydantic and SQLAlchemy."""

from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# ============================================================================
# PYDANTIC MODELS (API/validation)
# ============================================================================


class EventBase(BaseModel):
    """Base event schema."""

    title: str
    description: str
    source: str = Field(..., description="fred | edgar | gdelt | news | manual")
    source_url: str | None = None
    occurred_at: datetime
    raw_text: str


class EventCreate(EventBase):
    """Schema for creating a new event."""



class EventResponse(EventBase):
    """Schema for event API responses."""

    event_id: str
    entities: list[str] = []
    processed: bool = False
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================================
# SQLALCHEMY ORM MODELS (Database)
# ============================================================================


class EventORM(Base):
    """SQLAlchemy ORM model for Event storage in PostgreSQL."""

    __tablename__ = "events"

    event_id = Column(String(255), primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    source = Column(String(50), nullable=False, index=True)
    source_url = Column(String(2048), nullable=True)
    occurred_at = Column(DateTime, nullable=False, index=True)
    raw_text = Column(Text, nullable=False)
    entities = Column(JSON, default=list, nullable=False)
    processed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        """String representation of EventORM."""
        return f"<EventORM(event_id={self.event_id}, title={self.title}, source={self.source})>"

    def to_pydantic(self) -> EventResponse:
        """Convert ORM model to Pydantic model."""
        return EventResponse(
            event_id=self.event_id,
            title=self.title,
            description=self.description,
            source=self.source,
            source_url=self.source_url,
            occurred_at=self.occurred_at,
            raw_text=self.raw_text,
            entities=self.entities or [],
            processed=self.processed,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
