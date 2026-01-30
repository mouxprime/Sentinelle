"""Telegram collector using Telethon for user account."""
import asyncio
import hashlib
from datetime import datetime
from typing import List
from telethon import TelegramClient
from telethon.tl.types import Message
from loguru import logger
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Source, Event, SourceType
from ..database import SessionLocal


class TelegramCollector:
    """Collector for Telegram channels using user account."""

    def __init__(self):
        """Initialize Telegram collector."""
        self.client: TelegramClient = None
        self.is_running = False

    async def initialize(self):
        """Initialize Telegram client."""
        if not settings.telegram_api_id or not settings.telegram_api_hash:
            logger.warning("Telegram credentials not configured, collector disabled")
            return

        try:
            self.client = TelegramClient(
                f"/app/sessions/{settings.telegram_session_name}",
                settings.telegram_api_id,
                settings.telegram_api_hash
            )
            await self.client.start(phone=settings.telegram_phone)
            logger.info("Telegram client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram client: {e}")
            raise

    async def collect(self, limit_per_channel: int = 10):
        """Collect recent messages from configured channels."""
        if not self.client:
            logger.warning("Telegram client not initialized")
            return

        db = SessionLocal()
        try:
            for channel_username in settings.telegram_channels_list:
                try:
                    await self._collect_from_channel(db, channel_username, limit_per_channel)
                except Exception as e:
                    logger.error(f"Error collecting from {channel_username}: {e}")
                    continue
        finally:
            db.close()

    async def _collect_from_channel(self, db: Session, channel_username: str, limit: int):
        """Collect messages from a specific channel."""
        logger.info(f"Collecting from Telegram channel: {channel_username}")

        try:
            # Get or create source
            source = db.query(Source).filter(
                Source.type == SourceType.TELEGRAM,
                Source.name == channel_username
            ).first()

            if not source:
                source = Source(
                    name=channel_username,
                    type=SourceType.TELEGRAM,
                    url=f"https://t.me/{channel_username}",
                    is_active=True
                )
                db.add(source)
                db.commit()
                db.refresh(source)

            # Get recent messages
            messages = await self.client.get_messages(channel_username, limit=limit)

            collected_count = 0
            for message in messages:
                if not isinstance(message, Message) or not message.text:
                    continue

                # Create content hash for deduplication
                content_hash = hashlib.sha256(message.text.encode()).hexdigest()

                # Check if already exists
                existing = db.query(Event).filter(Event.content_hash == content_hash).first()
                if existing:
                    continue

                # Create new event
                event = Event(
                    source_id=source.id,
                    raw_content=message.text,
                    content_hash=content_hash,
                    collected_at=datetime.utcnow(),
                    event_time=message.date,
                    is_processed=False,
                    metadata={
                        "message_id": message.id,
                        "views": message.views if message.views else 0,
                        "forwards": message.forwards if message.forwards else 0,
                    }
                )
                db.add(event)
                collected_count += 1

            db.commit()
            logger.info(f"Collected {collected_count} new messages from {channel_username}")

        except Exception as e:
            db.rollback()
            logger.error(f"Error in _collect_from_channel for {channel_username}: {e}")
            raise

    async def stop(self):
        """Stop the Telegram client."""
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram client disconnected")


# Global collector instance
telegram_collector = TelegramCollector()
