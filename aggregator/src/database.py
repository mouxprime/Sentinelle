"""Database configuration and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    # Import all models here to ensure they are registered
    from . import models  # noqa
    from sqlalchemy import inspect
    from loguru import logger

    try:
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if not existing_tables:
            logger.info("Creating database schema...")
            Base.metadata.create_all(bind=engine, checkfirst=True)
            logger.info("Database schema created successfully")
        else:
            logger.info(f"Database already initialized with {len(existing_tables)} tables")
            # Try to create any missing tables/indexes
            Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        logger.warning(f"Database initialization warning (may be normal if already initialized): {e}")
        # Continue anyway as tables might already exist
