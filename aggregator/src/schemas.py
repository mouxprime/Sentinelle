"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from .models import ThreatLevel, EventCategory, SourceType


# Event Schemas
class EventBase(BaseModel):
    """Base event schema."""
    title: Optional[str] = None
    raw_content: str
    category: Optional[EventCategory] = None
    threat_level: Optional[ThreatLevel] = None
    summary: Optional[str] = None
    entities: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    country: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    event_time: Optional[datetime] = None


class EventCreate(EventBase):
    """Schema for creating events."""
    source_id: int
    metadata: Optional[Dict[str, Any]] = None


class EventResponse(EventBase):
    """Schema for event responses."""
    id: int
    source_id: int
    content_hash: str
    collected_at: datetime
    processed_at: Optional[datetime] = None
    is_processed: bool
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Schema for paginated event lists."""
    events: List[EventResponse]
    total: int
    page: int
    page_size: int


# Source Schemas
class SourceBase(BaseModel):
    """Base source schema."""
    name: str
    type: SourceType
    url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: bool = True


class SourceCreate(SourceBase):
    """Schema for creating sources."""
    pass


class SourceResponse(SourceBase):
    """Schema for source responses."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Alert Schemas
class AlertBase(BaseModel):
    """Base alert schema."""
    name: str
    keywords: Optional[List[str]] = None
    categories: Optional[List[EventCategory]] = None
    threat_levels: Optional[List[ThreatLevel]] = None
    countries: Optional[List[str]] = None
    bbox: Optional[List[float]] = Field(None, min_length=4, max_length=4)
    is_active: bool = True
    notification_channels: Optional[Dict[str, Any]] = None


class AlertCreate(AlertBase):
    """Schema for creating alerts."""
    pass


class AlertResponse(AlertBase):
    """Schema for alert responses."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Flight Schemas
class FlightResponse(BaseModel):
    """Schema for flight responses."""
    id: int
    flight_id: str
    callsign: Optional[str] = None
    aircraft_code: Optional[str] = None
    registration: Optional[str] = None
    airline: Optional[str] = None
    latitude: float
    longitude: float
    altitude: Optional[int] = None
    heading: Optional[int] = None
    speed: Optional[int] = None
    origin_airport: Optional[str] = None
    destination_airport: Optional[str] = None
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Vessel Schemas
class VesselResponse(BaseModel):
    """Schema for vessel responses."""
    id: int
    mmsi: int
    vessel_name: Optional[str] = None
    imo: Optional[int] = None
    vessel_type: Optional[str] = None
    flag: Optional[str] = None
    latitude: float
    longitude: float
    heading: Optional[int] = None
    speed: Optional[float] = None
    status: Optional[str] = None
    destination: Optional[str] = None
    eta: Optional[datetime] = None
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Stats Schema
class StatsResponse(BaseModel):
    """Schema for statistics response."""
    total_events: int
    events_by_category: Dict[str, int]
    events_by_threat_level: Dict[str, int]
    events_by_country: Dict[str, int]
    recent_events_count: int
    active_sources: int
    total_flights: Optional[int] = None
    total_vessels: Optional[int] = None
