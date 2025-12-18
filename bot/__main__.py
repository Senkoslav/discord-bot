"""
Entry point for the Discord Music Bot.
Run with: python -m bot
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from bot.core.bot import MusicBot
from bot.core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


async def main() -> None:
    """Main entry point for the bot."""
    config = Config()
    
    # Set log level from config
    logging.getLogger().setLevel(getattr(logging, config.log_level.upper()))
    
    bot: Optional[MusicBot] = None
    
    try:
        bot = MusicBot(config)
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        
        def signal_handler() -> None:
            logger.info("Received shutdown signal, closing bot...")
            asyncio.create_task(bot.close())
        
        # Register signal handlers (Unix only)
        if sys.platform != "win32":
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, signal_handler)
        
        logger.info("Starting Music Bot v%s", bot.__class__.__module__)
        await bot.start(config.discord_token)
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        sys.exit(1)
    finally:
        if bot and not bot.is_closed():
            await bot.close()
        logger.info("Bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
