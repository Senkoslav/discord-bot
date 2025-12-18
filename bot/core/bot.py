"""
Main bot class with cog loading and lifecycle management.
"""

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from bot.core.config import Config
    from bot.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class MusicBot(commands.Bot):
    """
    Main Discord bot class.
    
    Handles initialization, cog loading, and graceful shutdown.
    """
    
    def __init__(self, config: "Config") -> None:
        """
        Initialize the bot with configuration.
        
        Args:
            config: Bot configuration object
        """
        self.config = config
        self.db: Optional["DatabaseManager"] = None
        
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True  # For prefix commands
        intents.voice_states = True     # For voice channel tracking
        intents.guilds = True           # For guild events
        
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.command_prefix),
            intents=intents,
            help_command=None,  # We'll use slash commands primarily
        )
    
    async def setup_hook(self) -> None:
        """
        Called when the bot is starting up.
        Load cogs and initialize database.
        """
        logger.info("Running setup hook...")
        
        # Initialize database
        from bot.database.manager import DatabaseManager
        self.db = DatabaseManager(self.config)
        await self.db.initialize()
        logger.info("Database initialized")
        
        # Load cogs
        cogs = [
            "bot.cogs.music",
            "bot.cogs.admin",
            "bot.cogs.utility",
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info("Loaded cog: %s", cog)
            except Exception as e:
                logger.error("Failed to load cog %s: %s", cog, e)
        
        # Sync slash commands
        logger.info("Syncing slash commands...")
        await self.tree.sync()
        logger.info("Slash commands synced")
    
    async def on_ready(self) -> None:
        """Called when the bot is ready and connected."""
        if self.user:
            logger.info(
                "Bot is ready! Logged in as %s (ID: %s)",
                self.user.name,
                self.user.id,
            )
            logger.info("Connected to %d guilds", len(self.guilds))
        
        # Set presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play | Music Bot",
            )
        )
    
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Called when the bot joins a new guild."""
        logger.info("Joined guild: %s (ID: %s)", guild.name, guild.id)
    
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Called when the bot is removed from a guild."""
        logger.info("Left guild: %s (ID: %s)", guild.name, guild.id)
        
        # Clean up guild data
        if self.db:
            await self.db.clear_guild_queue(guild.id)
    
    async def close(self) -> None:
        """Graceful shutdown - cleanup resources."""
        logger.info("Shutting down bot...")
        
        # Disconnect from all voice channels
        for vc in self.voice_clients:
            try:
                await vc.disconnect(force=True)
            except Exception as e:
                logger.warning("Error disconnecting from voice: %s", e)
        
        # Close database connection
        if self.db:
            await self.db.close()
            logger.info("Database connection closed")
        
        await super().close()
