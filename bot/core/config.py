"""
Configuration management for the bot.
Loads settings from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

# Load .env file if present
load_dotenv()


@dataclass
class Config:
    """Bot configuration loaded from environment variables."""
    
    # Required
    discord_token: str = field(default_factory=lambda: os.getenv("DISCORD_TOKEN", ""))
    
    # Bot settings
    bot_owner_id: Optional[int] = field(
        default_factory=lambda: int(os.getenv("BOT_OWNER_ID", "0")) or None
    )
    command_prefix: str = field(default_factory=lambda: os.getenv("COMMAND_PREFIX", "!"))
    
    # Database
    use_redis: bool = field(
        default_factory=lambda: os.getenv("USE_REDIS", "false").lower() == "true"
    )
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    sqlite_path: str = field(
        default_factory=lambda: os.getenv("SQLITE_PATH", "data/music_bot.db")
    )
    
    # Audio settings
    default_volume: int = field(
        default_factory=lambda: int(os.getenv("DEFAULT_VOLUME", "100"))
    )
    max_queue_size: int = field(
        default_factory=lambda: int(os.getenv("MAX_QUEUE_SIZE", "500"))
    )
    inactivity_timeout: int = field(
        default_factory=lambda: int(os.getenv("INACTIVITY_TIMEOUT", "300"))
    )
    
    # Rate limiting
    rate_limit_commands: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_COMMANDS", "20"))
    )
    
    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    # Optional paths
    youtube_cookies_path: Optional[str] = field(
        default_factory=lambda: os.getenv("YOUTUBE_COOKIES_PATH")
    )
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.discord_token:
            raise ValueError(
                "DISCORD_TOKEN environment variable is required. "
                "Get your token from https://discord.com/developers/applications"
            )
        
        # Clamp volume to valid range
        self.default_volume = max(0, min(200, self.default_volume))
        
        # Ensure positive values
        self.max_queue_size = max(1, self.max_queue_size)
        self.inactivity_timeout = max(60, self.inactivity_timeout)
        self.rate_limit_commands = max(1, self.rate_limit_commands)
