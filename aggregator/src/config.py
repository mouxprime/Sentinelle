"""Configuration management using Pydantic Settings."""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Database
    postgres_user: str = "osint"
    postgres_password: str
    postgres_db: str = "osint_aggregator"
    postgres_host: str = "database"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # LLM Configuration
    llm_api_url: str = "http://host.docker.internal:1234/v1"
    llm_model: str = "qwen2.5-7b-instruct"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1000

    # Mapbox
    mapbox_token: str

    # Telegram Configuration
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_phone: Optional[str] = None
    telegram_channels: str = ""  # Comma-separated list
    telegram_session_name: str = "osint_session"

    @property
    def telegram_channels_list(self) -> List[str]:
        """Parse Telegram channels into list."""
        return [ch.strip() for ch in self.telegram_channels.split(",") if ch.strip()]

    # RSS Configuration
    rss_feeds: str = ""  # Comma-separated list

    @property
    def rss_feeds_list(self) -> List[str]:
        """Parse RSS feeds into list."""
        return [feed.strip() for feed in self.rss_feeds.split(",") if feed.strip()]

    # Discord Configuration (optional)
    discord_bot_token: Optional[str] = None
    discord_channels: str = ""  # Comma-separated list

    @property
    def discord_channels_list(self) -> List[str]:
        """Parse Discord channels into list."""
        return [ch.strip() for ch in self.discord_channels.split(",") if ch.strip()]

    # FlightRadar Configuration (optional)
    flightradar_enabled: bool = False
    flightradar_bounds: str = ""  # Format: "lat1,lon1,lat2,lon2"

    @property
    def flightradar_bounds_tuple(self) -> Optional[tuple]:
        """Parse FlightRadar bounds."""
        if not self.flightradar_bounds:
            return None
        try:
            coords = [float(x.strip()) for x in self.flightradar_bounds.split(",")]
            if len(coords) == 4:
                return tuple(coords)
        except ValueError:
            pass
        return None

    # MarineTraffic Configuration (optional)
    marinetraffic_enabled: bool = False
    marinetraffic_api_key: Optional[str] = None

    # Scheduler Configuration
    collection_interval_minutes: int = 5
    processing_interval_minutes: int = 2

    # API Configuration
    api_cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list."""
        if self.api_cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


# Global settings instance
settings = Settings()
