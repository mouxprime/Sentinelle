"""Events API routes."""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from geoalchemy2.shape import to_shape

from ..database import get_db
from ..models import Event, EventCategory, ThreatLevel
from ..schemas import EventResponse, EventCreate, EventListResponse

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=EventListResponse)
async def list_events(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    category: Optional[EventCategory] = None,
    threat_level: Optional[ThreatLevel] = None,
    country: Optional[str] = None,
    min_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lat: Optional[float] = None,
    max_lon: Optional[float] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
):
    """Get list of events with filters and pagination."""
    query = db.query(Event).filter(Event.is_processed == True)

    # Apply filters
    if category:
        query = query.filter(Event.category == category)

    if threat_level:
        query = query.filter(Event.threat_level == threat_level)

    if country:
        query = query.filter(Event.country.ilike(f"%{country}%"))

    # Bounding box filter
    if all(v is not None for v in [min_lat, min_lon, max_lat, max_lon]):
        query = query.filter(
            and_(
                Event.latitude >= min_lat,
                Event.latitude <= max_lat,
                Event.longitude >= min_lon,
                Event.longitude <= max_lon,
            )
        )

    # Date range filter
    if start_date:
        query = query.filter(Event.event_time >= start_date)
    if end_date:
        query = query.filter(Event.event_time <= end_date)

    # Search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Event.title.ilike(search_pattern),
                Event.summary.ilike(search_pattern),
                Event.raw_content.ilike(search_pattern),
            )
        )

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    events = query.order_by(Event.collected_at.desc()).offset(offset).limit(page_size).all()

    return EventListResponse(
        events=events,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: Session = Depends(get_db)):
    """Get a specific event by ID."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(event_data: EventCreate, db: Session = Depends(get_db)):
    """Create a new event manually."""
    import hashlib

    # Create content hash
    content_hash = hashlib.sha256(event_data.raw_content.encode()).hexdigest()

    # Check for duplicates
    existing = db.query(Event).filter(Event.content_hash == content_hash).first()
    if existing:
        raise HTTPException(status_code=409, detail="Event already exists")

    # Create event
    event = Event(
        **event_data.model_dump(exclude={"metadata"}),
        content_hash=content_hash,
        collected_at=datetime.utcnow(),
        is_processed=False
    )

    if event_data.metadata:
        event.event_metadata = event_data.metadata

    db.add(event)
    db.commit()
    db.refresh(event)

    return event


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: int, db: Session = Depends(get_db)):
    """Delete an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event)
    db.commit()

    return None
