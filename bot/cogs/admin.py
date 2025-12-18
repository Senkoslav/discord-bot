"""
Admin commands cog.
Owner-only and admin commands for bot management.
"""

import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.checks import is_owner, is_admin
from bot.utils.embeds import create_success_embed, create_error_embed, create_info_embed

if TYPE_CHECKING:
    from bot.core.bot import MusicBot

logger = logging.getLogger(__name__)


class AdminCog(commands.Cog, name="Admin"):
    """Administrative commands."""
    
    def __init__(self, bot: "MusicBot") -> None:
        self.bot = bot
    
    @app_commands.command(name="reload", description="Reload a cog (owner only)")
    @app_commands.describe(cog="Cog name to reload")
    @app_commands.choices(cog=[
        app_commands.Choice(name="Music", value="bot.cogs.music"),
        app_commands.Choice(name="Admin", value="bot.cogs.admin"),
        app_commands.Choice(name="Utility", value="bot.cogs.utility"),
    ])
    @is_owner()
    async def reload(self, interaction: discord.Interaction, cog: str) -> None:
        """Reload a cog."""
        try:
            await self.bot.reload_extension(cog)
            await interaction.response.send_message(
                embed=create_success_embed(f"Reloaded `{cog}`")
            )
            logger.info("Reloaded cog: %s", cog)
        except Exception as e:
            await interaction.response.send_message(
                embed=create_error_embed(f"Failed to reload `{cog}`: {e}"),
                ephemeral=True,
            )
            logger.error("Failed to reload cog %s: %s", cog, e)
    
    @app_commands.command(name="sync", description="Sync slash commands (owner only)")
    @app_commands.describe(guild_only="Sync to current guild only (faster)")
    @is_owner()
    async def sync(
        self,
        interaction: discord.Interaction,
        guild_only: bool = False,
    ) -> None:
        """Sync slash commands."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            if guild_only and interaction.guild:
                self.bot.tree.copy_global_to(guild=interaction.guild)
                synced = await self.bot.tree.sync(guild=interaction.guild)
                await interaction.followup.send(
                    embed=create_success_embed(
                        f"Synced {len(synced)} commands to this guild."
                    )
                )
            else:
                synced = await self.bot.tree.sync()
                await interaction.followup.send(
                    embed=create_success_embed(
                        f"Synced {len(synced)} commands globally."
                    )
                )
            logger.info("Synced %d commands", len(synced))
        except Exception as e:
            await interaction.followup.send(
                embed=create_error_embed(f"Failed to sync: {e}")
            )
            logger.error("Failed to sync commands: %s", e)
    
    @app_commands.command(name="status", description="Set bot status (owner only)")
    @app_commands.describe(
        activity_type="Activity type",
        text="Status text"
    )
    @app_commands.choices(activity_type=[
        app_commands.Choice(name="Playing", value="playing"),
        app_commands.Choice(name="Listening", value="listening"),
        app_commands.Choice(name="Watching", value="watching"),
    ])
    @is_owner()
    async def status(
        self,
        interaction: discord.Interaction,
        activity_type: str,
        text: str,
    ) -> None:
        """Set bot status."""
        activity_map = {
            "playing": discord.ActivityType.playing,
            "listening": discord.ActivityType.listening,
            "watching": discord.ActivityType.watching,
        }
        
        activity = discord.Activity(
            type=activity_map[activity_type],
            name=text,
        )
        
        await self.bot.change_presence(activity=activity)
        
        await interaction.response.send_message(
            embed=create_success_embed(f"Status set to: {activity_type} {text}"),
            ephemeral=True,
        )
    
    @app_commands.command(name="shutdown", description="Shutdown the bot (owner only)")
    @is_owner()
    async def shutdown(self, interaction: discord.Interaction) -> None:
        """Shutdown the bot gracefully."""
        await interaction.response.send_message(
            embed=create_info_embed("👋 Shutting down..."),
            ephemeral=True,
        )
        logger.info("Shutdown requested by %s", interaction.user)
        await self.bot.close()
    
    @app_commands.command(name="servers", description="List servers the bot is in (owner only)")
    @is_owner()
    async def servers(self, interaction: discord.Interaction) -> None:
        """List all servers."""
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        
        lines = []
        for guild in guilds[:20]:  # Limit to 20
            lines.append(f"• **{guild.name}** ({guild.member_count} members)")
        
        embed = create_info_embed(
            "\n".join(lines) if lines else "Not in any servers."
        )
        embed.title = f"📊 Servers ({len(self.bot.guilds)} total)"
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="announce", description="Send announcement to all servers (owner only)")
    @app_commands.describe(message="Announcement message")
    @is_owner()
    async def announce(self, interaction: discord.Interaction, message: str) -> None:
        """Send announcement to all servers."""
        await interaction.response.defer(ephemeral=True)
        
        sent = 0
        failed = 0
        
        for guild in self.bot.guilds:
            # Try to find a suitable channel
            channel = (
                guild.system_channel
                or discord.utils.find(
                    lambda c: c.permissions_for(guild.me).send_messages,
                    guild.text_channels,
                )
            )
            
            if channel:
                try:
                    embed = discord.Embed(
                        title="📢 Announcement",
                        description=message,
                        color=0x5865F2,
                    )
                    embed.set_footer(text=f"From {self.bot.user.name if self.bot.user else 'Bot'}")
                    await channel.send(embed=embed)
                    sent += 1
                except Exception:
                    failed += 1
            else:
                failed += 1
        
        await interaction.followup.send(
            embed=create_success_embed(
                f"Announcement sent to {sent} servers. Failed: {failed}"
            )
        )


async def setup(bot: "MusicBot") -> None:
    """Setup function for loading the cog."""
    await bot.add_cog(AdminCog(bot))
