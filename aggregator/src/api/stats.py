"""Statistics API routes."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Event, Source, Flight, Vessel
from ..schemas import StatsResponse

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Get platform statistics."""

    # Total events
    total_events = db.query(func.count(Event.id)).filter(Event.is_processed == True).scalar()

    # Events by category
    category_stats = db.query(
        Event.category,
        func.count(Event.id)
    ).filter(Event.is_processed == True).group_by(Event.category).all()

    events_by_category = {
        str(cat): count for cat, count in category_stats if cat
    }

    # Events by threat level
    threat_stats = db.query(
        Event.threat_level,
        func.count(Event.id)
    ).filter(Event.is_processed == True).group_by(Event.threat_level).all()

    events_by_threat_level = {
        str(level): count for level, count in threat_stats if level
    }

    # Events by country (top 10)
    country_stats = db.query(
        Event.country,
        func.count(Event.id)
    ).filter(
        Event.is_processed == True,
        Event.country.isnot(None)
    ).group_by(Event.country).order_by(func.count(Event.id).desc()).limit(10).all()

    events_by_country = {
        country: count for country, count in country_stats
    }

    # Recent events (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_events_count = db.query(func.count(Event.id)).filter(
        Event.is_processed == True,
        Event.collected_at >= yesterday
    ).scalar()

    # Active sources
    active_sources = db.query(func.count(Source.id)).filter(Source.is_active == True).scalar()

    # Flight stats (if table exists)
    try:
        total_flights = db.query(func.count(Flight.id)).scalar()
    except:
        total_flights = None

    # Vessel stats (if table exists)
    try:
        total_vessels = db.query(func.count(Vessel.id)).scalar()
    except:
        total_vessels = None

    return StatsResponse(
        total_events=total_events or 0,
        events_by_category=events_by_category,
        events_by_threat_level=events_by_threat_level,
        events_by_country=events_by_country,
        recent_events_count=recent_events_count or 0,
        active_sources=active_sources or 0,
        total_flights=total_flights,
        total_vessels=total_vessels,
    )
