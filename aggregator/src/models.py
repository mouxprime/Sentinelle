"""Database models using SQLAlchemy with PostGIS support."""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Float,
    ForeignKey,
    Index,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
import enum

from .database import Base


class ThreatLevel(str, enum.Enum):
    """Threat level enumeration."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EventCategory(str, enum.Enum):
    """Event category enumeration."""
    CONFLICT = "conflict"
    PROTEST = "protest"
    DISASTER = "disaster"
    DIPLOMATIC = "diplomatic"
    MILITARY = "military"
    CYBER = "cyber"
    TERRORISM = "terrorism"
    OTHER = "other"


class SourceType(str, enum.Enum):
    """Source type enumeration."""
    TELEGRAM = "telegram"
    RSS = "rss"
    DISCORD = "discord"
    FLIGHTRADAR = "flightradar"
    MARINETRAFFIC = "marinetraffic"
    MANUAL = "manual"


class Source(Base):
    """Data sources table."""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(SourceType), nullable=False)
    url = Column(String(500))
    config = Column(JSON)  # Source-specific configuration
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    events = relationship("Event", back_populates="source")

    __table_args__ = (
        Index("idx_sources_type", "type"),
        Index("idx_sources_active", "is_active"),
    )


class Event(Base):
    """Events table with geospatial support."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)

    # Content
    title = Column(String(500))
    raw_content = Column(Text, nullable=False)
    content_hash = Column(String(64), unique=True, index=True)  # For deduplication

    # Classification (filled by LLM)
    category = Column(SQLEnum(EventCategory))
    threat_level = Column(SQLEnum(ThreatLevel))
    summary = Column(Text)
    entities = Column(JSON)  # List of entities mentioned
    keywords = Column(JSON)  # List of keywords

    # Geolocation (PostGIS Point)
    location = Column(Geometry("POINT", srid=4326))
    country = Column(String(100))
    location_name = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)

    # Timing
    event_time = Column(DateTime)  # When the event occurred
    collected_at = Column(DateTime, default=datetime.utcnow)  # When we collected it
    processed_at = Column(DateTime)  # When LLM processed it

    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_error = Column(Text)

    # Metadata
    metadata = Column(JSON)  # Additional source-specific metadata

    # Relationships
    source = relationship("Source", back_populates="events")

    __table_args__ = (
        Index("idx_events_category", "category"),
        Index("idx_events_threat_level", "threat_level"),
        Index("idx_events_country", "country"),
        Index("idx_events_processed", "is_processed"),
        Index("idx_events_event_time", "event_time"),
        Index("idx_events_collected_at", "collected_at"),
        Index("idx_events_location", "location", postgresql_using="gist"),  # Spatial index
    )


class Alert(Base):
    """User alert rules table."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    # Alert conditions
    keywords = Column(JSON)  # List of keywords to match
    categories = Column(JSON)  # List of EventCategory values
    threat_levels = Column(JSON)  # List of ThreatLevel values
    countries = Column(JSON)  # List of country names
    bbox = Column(JSON)  # Bounding box [minLon, minLat, maxLon, maxLat]

    # Alert settings
    is_active = Column(Boolean, default=True)
    notification_channels = Column(JSON)  # email, webhook, etc.

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_alerts_active", "is_active"),
    )


class Flight(Base):
    """FlightRadar24 data table."""
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, index=True)
    flight_id = Column(String(50), unique=True, index=True)

    # Flight details
    callsign = Column(String(20))
    aircraft_code = Column(String(10))
    registration = Column(String(20))
    airline = Column(String(100))

    # Position
    location = Column(Geometry("POINT", srid=4326))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Integer)  # feet
    heading = Column(Integer)  # degrees
    speed = Column(Integer)  # knots

    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Origin/Destination
    origin_airport = Column(String(4))
    destination_airport = Column(String(4))

    # Metadata
    metadata = Column(JSON)

    __table_args__ = (
        Index("idx_flights_callsign", "callsign"),
        Index("idx_flights_timestamp", "timestamp"),
        Index("idx_flights_location", "location", postgresql_using="gist"),
    )


class Vessel(Base):
    """MarineTraffic data table."""
    __tablename__ = "vessels"

    id = Column(Integer, primary_key=True, index=True)
    mmsi = Column(Integer, unique=True, index=True)  # Maritime Mobile Service Identity

    # Vessel details
    vessel_name = Column(String(255))
    imo = Column(Integer)  # International Maritime Organization number
    vessel_type = Column(String(100))
    flag = Column(String(50))

    # Position
    location = Column(Geometry("POINT", srid=4326))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    heading = Column(Integer)  # degrees
    speed = Column(Float)  # knots

    # Status
    status = Column(String(50))
    destination = Column(String(255))
    eta = Column(DateTime)

    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Metadata
    metadata = Column(JSON)

    __table_args__ = (
        Index("idx_vessels_name", "vessel_name"),
        Index("idx_vessels_type", "vessel_type"),
        Index("idx_vessels_timestamp", "timestamp"),
        Index("idx_vessels_location", "location", postgresql_using="gist"),
    )
