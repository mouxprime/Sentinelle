"""Scheduler for periodic data collection and processing."""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from .config import settings
from .collectors.telegram_collector import telegram_collector
from .collectors.rss_collector import rss_collector
from .processors.llm_processor import llm_processor


class DataScheduler:
    """Manages periodic data collection and processing tasks."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting data scheduler")

        # Initialize collectors
        try:
            await telegram_collector.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize Telegram collector: {e}")

        # Schedule collection tasks
        collection_interval = settings.collection_interval_minutes
        processing_interval = settings.processing_interval_minutes

        # Telegram collection
        if settings.telegram_channels_list:
            self.scheduler.add_job(
                telegram_collector.collect,
                trigger=IntervalTrigger(minutes=collection_interval),
                id="telegram_collection",
                name="Telegram Collection",
                replace_existing=True
            )
            logger.info(f"Scheduled Telegram collection every {collection_interval} minutes")

        # RSS collection
        if settings.rss_feeds_list:
            self.scheduler.add_job(
                rss_collector.collect,
                trigger=IntervalTrigger(minutes=collection_interval),
                id="rss_collection",
                name="RSS Collection",
                replace_existing=True
            )
            logger.info(f"Scheduled RSS collection every {collection_interval} minutes")

        # LLM processing
        self.scheduler.add_job(
            llm_processor.process_pending_events,
            trigger=IntervalTrigger(minutes=processing_interval),
            id="llm_processing",
            name="LLM Processing",
            replace_existing=True
        )
        logger.info(f"Scheduled LLM processing every {processing_interval} minutes")

        # Start scheduler
        self.scheduler.start()
        self.is_running = True

        logger.info("Data scheduler started successfully")

    async def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return

        logger.info("Stopping data scheduler")

        # Stop Telegram collector
        await telegram_collector.stop()

        # Shutdown scheduler
        self.scheduler.shutdown(wait=False)
        self.is_running = False

        logger.info("Data scheduler stopped")

    async def run_collection_now(self):
        """Trigger collection immediately (manual trigger)."""
        logger.info("Running manual collection")

        tasks = []

        if settings.telegram_channels_list:
            tasks.append(telegram_collector.collect())

        if settings.rss_feeds_list:
            tasks.append(rss_collector.collect())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Manual collection completed")

    async def run_processing_now(self):
        """Trigger LLM processing immediately (manual trigger)."""
        logger.info("Running manual processing")
        await llm_processor.process_pending_events(batch_size=50)
        logger.info("Manual processing completed")


# Global scheduler instance
data_scheduler = DataScheduler()
