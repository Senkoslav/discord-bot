"""
Permission checks and decorators for commands.
"""

import time
from collections import defaultdict
from functools import wraps
from typing import Callable, Optional

import discord
from discord import app_commands
from discord.ext import commands


class RateLimiter:
    """
    Simple rate limiter for commands.
    
    Tracks command usage per user and enforces limits.
    """
    
    def __init__(self, max_calls: int = 20, period: int = 60) -> None:
        """
        Initialize rate limiter.
        
        Args:
            max_calls: Maximum calls allowed per period
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self._calls: dict[int, list[float]] = defaultdict(list)
    
    def is_limited(self, user_id: int) -> bool:
        """
        Check if user is rate limited.
        
        Args:
            user_id: Discord user ID
        
        Returns:
            True if user is rate limited
        """
        now = time.time()
        calls = self._calls[user_id]
        
        # Remove old calls
        calls[:] = [t for t in calls if now - t < self.period]
        
        if len(calls) >= self.max_calls:
            return True
        
        calls.append(now)
        return False
    
    def get_retry_after(self, user_id: int) -> float:
        """Get seconds until rate limit resets."""
        if not self._calls[user_id]:
            return 0
        
        oldest = min(self._calls[user_id])
        return max(0, self.period - (time.time() - oldest))


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(max_calls: int = 20) -> RateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(max_calls=max_calls)
    return _rate_limiter


def is_in_voice() -> Callable:
    """
    Check that user is in a voice channel.
    
    For slash commands.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ You need to be in a voice channel to use this command.",
                ephemeral=True,
            )
            return False
        
        return True
    
    return app_commands.check(predicate)


def is_in_same_voice() -> Callable:
    """
    Check that user is in the same voice channel as the bot.
    
    For slash commands.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "❌ You need to be in a voice channel to use this command.",
                ephemeral=True,
            )
            return False
        
        # Check if bot is in voice
        if interaction.guild and interaction.guild.voice_client:
            bot_channel = interaction.guild.voice_client.channel
            if bot_channel and bot_channel != interaction.user.voice.channel:
                await interaction.response.send_message(
                    f"❌ You need to be in {bot_channel.mention} to use this command.",
                    ephemeral=True,
                )
                return False
        
        return True
    
    return app_commands.check(predicate)


def is_dj_or_admin() -> Callable:
    """
    Check that user has DJ role or admin permissions.
    
    DJ role is determined by:
    1. Having 'DJ' role (case-insensitive)
    2. Having manage_guild permission
    3. Being alone in voice channel with bot
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        
        # Admin always passes
        if interaction.user.guild_permissions.manage_guild:
            return True
        
        # Check for DJ role
        dj_role = discord.utils.find(
            lambda r: r.name.lower() == "dj",
            interaction.user.roles,
        )
        if dj_role:
            return True
        
        # Check if alone in voice with bot
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
            members = [m for m in channel.members if not m.bot]
            if len(members) == 1:
                return True
        
        await interaction.response.send_message(
            "❌ You need the DJ role or Manage Server permission to use this command.",
            ephemeral=True,
        )
        return False
    
    return app_commands.check(predicate)


def is_admin() -> Callable:
    """Check that user has manage_guild permission."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ You need Manage Server permission to use this command.",
                ephemeral=True,
            )
            return False
        
        return True
    
    return app_commands.check(predicate)


def is_owner() -> Callable:
    """Check that user is bot owner."""
    async def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client
        
        # Check against configured owner ID
        if hasattr(bot, "config") and bot.config.bot_owner_id:
            if interaction.user.id == bot.config.bot_owner_id:
                return True
        
        # Check against application owner
        if bot.application:
            if bot.application.owner and interaction.user.id == bot.application.owner.id:
                return True
            if bot.application.team:
                if interaction.user.id in [m.id for m in bot.application.team.members]:
                    return True
        
        await interaction.response.send_message(
            "❌ This command is only available to the bot owner.",
            ephemeral=True,
        )
        return False
    
    return app_commands.check(predicate)


def rate_limited() -> Callable:
    """Apply rate limiting to command."""
    async def predicate(interaction: discord.Interaction) -> bool:
        limiter = get_rate_limiter()
        
        if limiter.is_limited(interaction.user.id):
            retry_after = limiter.get_retry_after(interaction.user.id)
            await interaction.response.send_message(
                f"⏳ You're using commands too fast. Try again in {retry_after:.1f}s.",
                ephemeral=True,
            )
            return False
        
        return True
    
    return app_commands.check(predicate)
