"""
Utility commands cog.
General utility and info commands.
"""

import platform
import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.checks import rate_limited
from bot.utils.embeds import create_info_embed, create_success_embed, create_error_embed

if TYPE_CHECKING:
    from bot.core.bot import MusicBot

# Bot start time for uptime calculation
_start_time = time.time()


class UtilityCog(commands.Cog, name="Utility"):
    """Utility and info commands."""
    
    def __init__(self, bot: "MusicBot") -> None:
        self.bot = bot
    
    @app_commands.command(name="ping", description="Check bot latency")
    @rate_limited()
    async def ping(self, interaction: discord.Interaction) -> None:
        """Check bot latency."""
        latency = round(self.bot.latency * 1000)
        
        # Color based on latency
        if latency < 100:
            color = 0x43B581  # Green
            status = "Excellent"
        elif latency < 200:
            color = 0xFAA61A  # Yellow
            status = "Good"
        else:
            color = 0xF04747  # Red
            status = "Poor"
        
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**Latency:** {latency}ms ({status})",
            color=color,
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="info", description="Show bot information")
    @rate_limited()
    async def info(self, interaction: discord.Interaction) -> None:
        """Show bot information."""
        # Calculate uptime
        uptime_seconds = int(time.time() - _start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            uptime_str = f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            uptime_str = f"{hours}h {minutes}m {seconds}s"
        else:
            uptime_str = f"{minutes}m {seconds}s"
        
        embed = discord.Embed(
            title="🎵 Music Bot Info",
            color=0x5865F2,
        )
        
        # Bot stats
        embed.add_field(
            name="📊 Stats",
            value=(
                f"**Servers:** {len(self.bot.guilds)}\n"
                f"**Uptime:** {uptime_str}\n"
                f"**Latency:** {round(self.bot.latency * 1000)}ms"
            ),
            inline=True,
        )
        
        # System info
        embed.add_field(
            name="⚙️ System",
            value=(
                f"**Python:** {platform.python_version()}\n"
                f"**discord.py:** {discord.__version__}\n"
                f"**Platform:** {platform.system()}"
            ),
            inline=True,
        )
        
        # Features
        embed.add_field(
            name="🎶 Features",
            value=(
                "• YouTube & SoundCloud support\n"
                "• Queue management\n"
                "• Loop & shuffle modes\n"
                "• Volume control\n"
                "• Playlist support"
            ),
            inline=False,
        )
        
        embed.set_footer(text="Use /help for command list")
        
        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="help", description="Show available commands")
    @rate_limited()
    async def help(self, interaction: discord.Interaction) -> None:
        """Show help information."""
        embed = discord.Embed(
            title="🎵 Music Bot Commands",
            description="Here are all available commands:",
            color=0x5865F2,
        )
        
        # Music commands
        embed.add_field(
            name="🎶 Music",
            value=(
                "`/play <query>` - Play a song\n"
                "`/search <query>` - Search and choose\n"
                "`/pause` - Pause playback\n"
                "`/resume` - Resume playback\n"
                "`/skip` - Skip current track\n"
                "`/stop` - Stop and clear queue\n"
                "`/seek <seconds>` - Seek position"
            ),
            inline=True,
        )
        
        # Queue commands
        embed.add_field(
            name="📜 Queue",
            value=(
                "`/queue` - Show queue\n"
                "`/now` - Current track\n"
                "`/remove <pos>` - Remove track\n"
                "`/clear` - Clear queue\n"
                "`/shuffle` - Shuffle queue\n"
                "`/loop <mode>` - Set loop mode"
            ),
            inline=True,
        )
        
        # Other commands
        embed.add_field(
            name="⚙️ Other",
            value=(
                "`/volume <0-200>` - Set volume\n"
                "`/join` - Join voice\n"
                "`/leave` - Leave voice\n"
                "`/ping` - Check latency\n"
                "`/info` - Bot info\n"
                "`/playlist` - Manage playlists"
            ),
            inline=True,
        )
        
        embed.set_footer(text="Tip: You need to be in a voice channel to use music commands")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="invite", description="Get bot invite link")
    @rate_limited()
    async def invite(self, interaction: discord.Interaction) -> None:
        """Get bot invite link."""
        if not self.bot.user:
            await interaction.response.send_message(
                embed=create_error_embed("Bot is not ready yet."),
                ephemeral=True,
            )
            return
        
        permissions = discord.Permissions(
            send_messages=True,
            embed_links=True,
            connect=True,
            speak=True,
            use_voice_activation=True,
        )
        
        invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=permissions,
            scopes=["bot", "applications.commands"],
        )
        
        embed = discord.Embed(
            title="🔗 Invite Music Bot",
            description=f"[Click here to invite the bot]({invite_url})",
            color=0x5865F2,
        )
        
        await interaction.response.send_message(embed=embed)
    
    # Playlist commands group
    playlist_group = app_commands.Group(
        name="playlist",
        description="Manage your personal playlists"
    )
    
    @playlist_group.command(name="save", description="Save current queue as a playlist")
    @app_commands.describe(name="Playlist name")
    @rate_limited()
    async def playlist_save(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        """Save current queue as playlist."""
        if not interaction.guild:
            return
        
        # Get music cog to access player
        music_cog = self.bot.get_cog("Music")
        if not music_cog or not hasattr(music_cog, "get_player"):
            await interaction.response.send_message(
                embed=create_error_embed("Music system not available."),
                ephemeral=True,
            )
            return
        
        player = music_cog.get_player(interaction.guild.id)
        
        if player.queue.is_empty:
            await interaction.response.send_message(
                embed=create_error_embed("Queue is empty. Nothing to save."),
                ephemeral=True,
            )
            return
        
        if not self.bot.db:
            await interaction.response.send_message(
                embed=create_error_embed("Database not available."),
                ephemeral=True,
            )
            return
        
        success = await self.bot.db.save_playlist(
            interaction.user.id,
            name,
            player.queue.tracks,
        )
        
        if success:
            await interaction.response.send_message(
                embed=create_success_embed(
                    f"Saved playlist **{name}** with {player.queue.size} tracks."
                )
            )
        else:
            await interaction.response.send_message(
                embed=create_error_embed("Failed to save playlist."),
                ephemeral=True,
            )
    
    @playlist_group.command(name="load", description="Load a saved playlist")
    @app_commands.describe(name="Playlist name")
    @rate_limited()
    async def playlist_load(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        """Load a saved playlist."""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        
        if not self.bot.db:
            await interaction.response.send_message(
                embed=create_error_embed("Database not available."),
                ephemeral=True,
            )
            return
        
        await interaction.response.defer()
        
        tracks_data = await self.bot.db.load_playlist(interaction.user.id, name)
        
        if not tracks_data:
            await interaction.followup.send(
                embed=create_error_embed(f"Playlist **{name}** not found.")
            )
            return
        
        # Get music cog
        music_cog = self.bot.get_cog("Music")
        if not music_cog or not hasattr(music_cog, "get_player"):
            await interaction.followup.send(
                embed=create_error_embed("Music system not available.")
            )
            return
        
        player = music_cog.get_player(interaction.guild.id)
        
        # Connect to voice if needed
        if not player.is_connected:
            if interaction.user.voice and interaction.user.voice.channel:
                await player.connect(interaction.user.voice.channel)
        
        # Convert to Track objects
        from bot.music.track import Track
        tracks = [Track.from_dict(t) for t in tracks_data]
        
        # Update requester info
        for track in tracks:
            track.requester_id = interaction.user.id
            track.requester_name = interaction.user.display_name
        
        added = await player.add_tracks(tracks)
        
        if not player.is_playing:
            await player.play()
        
        await interaction.followup.send(
            embed=create_success_embed(
                f"Loaded playlist **{name}** with {added} tracks."
            )
        )
    
    @playlist_group.command(name="list", description="List your saved playlists")
    @rate_limited()
    async def playlist_list(self, interaction: discord.Interaction) -> None:
        """List saved playlists."""
        if not self.bot.db:
            await interaction.response.send_message(
                embed=create_error_embed("Database not available."),
                ephemeral=True,
            )
            return
        
        playlists = await self.bot.db.list_playlists(interaction.user.id)
        
        if not playlists:
            await interaction.response.send_message(
                embed=create_info_embed(
                    "You don't have any saved playlists.\n"
                    "Use `/playlist save <name>` to save the current queue."
                )
            )
            return
        
        embed = discord.Embed(
            title="📋 Your Playlists",
            description="\n".join(f"• **{name}**" for name in playlists),
            color=0x5865F2,
        )
        embed.set_footer(text="Use /playlist load <name> to load a playlist")
        
        await interaction.response.send_message(embed=embed)
    
    @playlist_group.command(name="delete", description="Delete a saved playlist")
    @app_commands.describe(name="Playlist name")
    @rate_limited()
    async def playlist_delete(
        self,
        interaction: discord.Interaction,
        name: str,
    ) -> None:
        """Delete a saved playlist."""
        if not self.bot.db:
            await interaction.response.send_message(
                embed=create_error_embed("Database not available."),
                ephemeral=True,
            )
            return
        
        success = await self.bot.db.delete_playlist(interaction.user.id, name)
        
        if success:
            await interaction.response.send_message(
                embed=create_success_embed(f"Deleted playlist **{name}**.")
            )
        else:
            await interaction.response.send_message(
                embed=create_error_embed(f"Playlist **{name}** not found."),
                ephemeral=True,
            )


async def setup(bot: "MusicBot") -> None:
    """Setup function for loading the cog."""
    await bot.add_cog(UtilityCog(bot))
