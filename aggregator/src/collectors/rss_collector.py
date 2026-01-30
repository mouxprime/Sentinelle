"""RSS feed collector."""
import hashlib
from datetime import datetime
from typing import List
import feedparser
from loguru import logger
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Source, Event, SourceType
from ..database import SessionLocal


class RSSCollector:
    """Collector for RSS feeds."""

    def __init__(self):
        """Initialize RSS collector."""
        self.is_running = False

    async def collect(self):
        """Collect from all configured RSS feeds."""
        if not settings.rss_feeds_list:
            logger.info("No RSS feeds configured")
            return

        db = SessionLocal()
        try:
            for feed_url in settings.rss_feeds_list:
                try:
                    await self._collect_from_feed(db, feed_url)
                except Exception as e:
                    logger.error(f"Error collecting from {feed_url}: {e}")
                    continue
        finally:
            db.close()

    async def _collect_from_feed(self, db: Session, feed_url: str):
        """Collect entries from a specific RSS feed."""
        logger.info(f"Collecting from RSS feed: {feed_url}")

        try:
            # Parse feed
            feed = feedparser.parse(feed_url)

            if feed.bozo:  # Feed parsing error
                logger.warning(f"Feed parsing error for {feed_url}: {feed.bozo_exception}")

            # Get or create source
            source = db.query(Source).filter(
                Source.type == SourceType.RSS,
                Source.url == feed_url
            ).first()

            if not source:
                feed_title = feed.feed.get("title", feed_url)
                source = Source(
                    name=feed_title,
                    type=SourceType.RSS,
                    url=feed_url,
                    is_active=True
                )
                db.add(source)
                db.commit()
                db.refresh(source)

            # Process entries
            collected_count = 0
            for entry in feed.entries:
                # Get entry content
                content = entry.get("summary", entry.get("description", ""))
                title = entry.get("title", "")
                full_content = f"{title}\n\n{content}" if title else content

                if not full_content:
                    continue

                # Create content hash
                content_hash = hashlib.sha256(full_content.encode()).hexdigest()

                # Check if already exists
                existing = db.query(Event).filter(Event.content_hash == content_hash).first()
                if existing:
                    continue

                # Parse published date
                event_time = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    event_time = datetime(*entry.published_parsed[:6])

                # Create new event
                event = Event(
                    source_id=source.id,
                    title=title,
                    raw_content=full_content,
                    content_hash=content_hash,
                    collected_at=datetime.utcnow(),
                    event_time=event_time,
                    is_processed=False,
                    metadata={
                        "link": entry.get("link"),
                        "author": entry.get("author"),
                        "tags": [tag.term for tag in entry.get("tags", [])]
                    }
                )
                db.add(event)
                collected_count += 1

            db.commit()
            logger.info(f"Collected {collected_count} new entries from {feed_url}")

        except Exception as e:
            db.rollback()
            logger.error(f"Error in _collect_from_feed for {feed_url}: {e}")
            raise


# Global collector instance
rss_collector = RSSCollector()
