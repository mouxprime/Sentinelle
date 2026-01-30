"""LLM processor for event classification and extraction using LM Studio."""
import json
from datetime import datetime
from typing import Dict, Any, Optional
from openai import OpenAI
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from loguru import logger
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Event, EventCategory, ThreatLevel
from ..database import SessionLocal


class LLMProcessor:
    """Process events using LLM for classification and information extraction."""

    SYSTEM_PROMPT = """You are an OSINT (Open Source Intelligence) analyst AI.
Your task is to analyze text from various sources (news, social media, etc.) and extract structured information about security events, geopolitical developments, and threat indicators.

For each text, extract the following information in JSON format:
{
  "category": "one of: conflict, protest, disaster, diplomatic, military, cyber, terrorism, other",
  "threat_level": "one of: critical, high, medium, low, info",
  "summary": "concise 1-2 sentence summary of the event",
  "entities": ["list", "of", "relevant", "entities", "mentioned"],
  "keywords": ["list", "of", "key", "terms"],
  "location": "primary location mentioned (city, region, or country)",
  "country": "country code or name",
  "event_time": "estimated time of event if mentioned, otherwise null"
}

Be precise and objective. If information is not available, use null."""

    def __init__(self):
        """Initialize LLM processor."""
        self.client = OpenAI(
            base_url=settings.llm_api_url,
            api_key="not-needed"  # LM Studio doesn't require API key
        )
        self.geocoder = Nominatim(user_agent="osint_aggregator")

    async def process_pending_events(self, batch_size: int = 10):
        """Process pending events in batches."""
        db = SessionLocal()
        try:
            # Get unprocessed events
            events = db.query(Event).filter(
                Event.is_processed == False,
                Event.processing_error.is_(None)
            ).limit(batch_size).all()

            if not events:
                logger.info("No pending events to process")
                return

            logger.info(f"Processing {len(events)} events")

            for event in events:
                try:
                    await self._process_event(db, event)
                    db.commit()
                except Exception as e:
                    logger.error(f"Error processing event {event.id}: {e}")
                    event.processing_error = str(e)
                    db.commit()

        finally:
            db.close()

    async def _process_event(self, db: Session, event: Event):
        """Process a single event."""
        logger.debug(f"Processing event {event.id}")

        try:
            # Call LLM
            extracted_data = await self._extract_with_llm(event.raw_content)

            # Update event with extracted data
            if extracted_data.get("category"):
                try:
                    event.category = EventCategory(extracted_data["category"])
                except ValueError:
                    event.category = EventCategory.OTHER

            if extracted_data.get("threat_level"):
                try:
                    event.threat_level = ThreatLevel(extracted_data["threat_level"])
                except ValueError:
                    event.threat_level = ThreatLevel.INFO

            event.summary = extracted_data.get("summary")
            event.entities = extracted_data.get("entities", [])
            event.keywords = extracted_data.get("keywords", [])
            event.country = extracted_data.get("country")

            # Geocode location
            location_name = extracted_data.get("location")
            if location_name:
                coords = await self._geocode(location_name)
                if coords:
                    event.latitude = coords["lat"]
                    event.longitude = coords["lon"]
                    event.location_name = location_name

                    # Create PostGIS Point
                    point = Point(coords["lon"], coords["lat"])
                    event.location = from_shape(point, srid=4326)

            # Mark as processed
            event.is_processed = True
            event.processed_at = datetime.utcnow()

            logger.info(f"Successfully processed event {event.id}")

        except Exception as e:
            logger.error(f"Error in _process_event for event {event.id}: {e}")
            raise

    async def _extract_with_llm(self, text: str) -> Dict[str, Any]:
        """Extract structured data from text using LLM."""
        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze this text:\n\n{text}"}
                ],
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )

            # Parse JSON response
            content = response.choices[0].message.content.strip()

            # Try to extract JSON from response (LLM might add extra text)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            extracted = json.loads(content)
            return extracted

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Raw response: {content}")
            return {}
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            return {}

    async def _geocode(self, location_name: str) -> Optional[Dict[str, float]]:
        """Geocode a location name to coordinates."""
        try:
            location = self.geocoder.geocode(location_name, timeout=10)
            if location:
                return {
                    "lat": location.latitude,
                    "lon": location.longitude
                }
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            logger.warning(f"Geocoding error for '{location_name}': {e}")
        except Exception as e:
            logger.error(f"Unexpected geocoding error for '{location_name}': {e}")

        return None


# Global processor instance
llm_processor = LLMProcessor()
