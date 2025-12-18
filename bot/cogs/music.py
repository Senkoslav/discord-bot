"""
Music commands cog.
Handles all music playback related slash commands.
"""

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.music.player import MusicPlayer
from bot.music.queue import LoopMode
from bot.music.track import Track
from bot.utils.checks import is_in_voice, is_in_same_voice, is_dj_or_admin, rate_limited
from bot.utils.embeds import (
    create_track_embed,
    create_queue_embed,
    create_search_embed,
    create_error_embed,
    create_success_embed,
    create_info_embed,
)

if TYPE_CHECKING:
    from bot.core.bot import MusicBot

logger = logging.getLogger(__name__)


class MusicCog(commands.Cog, name="Music"):
    """Music playback commands."""
    
    def __init__(self, bot: "MusicBot") -> None:
        self.bot = bot
        self._players: dict[int, MusicPlayer] = {}
    
    def get_player(self, guild_id: int) -> MusicPlayer:
        """Get or create player for guild."""
        if guild_id not in self._players:
            self._players[guild_id] = MusicPlayer(
                guild_id,
                self.bot.config,
                self.bot.db,
            )
        return self._players[guild_id]
    
    async def cog_unload(self) -> None:
        """Cleanup when cog is unloaded."""
        for player in self._players.values():
            await player.disconnect()
        self._players.clear()
    
    # ==================== Play Commands ====================
    
    @app_commands.command(name="play", description="Play a song from URL or search query")
    @app_commands.describe(query="YouTube/SoundCloud URL or search query")
    @is_in_voice()
    @rate_limited()
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        """Play a song or add it to the queue."""
        await interaction.response.defer()
        
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        
        player = self.get_player(interaction.guild.id)
        
        # Connect to voice if not connected
        if not player.is_connected:
            if interaction.user.voice and interaction.user.voice.channel:
                connected = await player.connect(interaction.user.voice.channel)
                if not connected:
                    await interaction.followup.send(
                        embed=create_error_embed("Failed to connect to voice channel.")
                    )
                    return
        
        # Extract tracks
        tracks = await player.extractor.extract(
            query,
            interaction.user.id,
            interaction.user.display_name,
        )
        
        if not tracks:
            await interaction.followup.send(
                embed=create_error_embed(
                    f"No results found for: `{query}`\n"
                    "Make sure the URL is valid or try a different search query."
                )
            )
            return
        
        # Add tracks to queue
        added = await player.add_tracks(tracks)
        
        if added == 0:
            await interaction.followup.send(
                embed=create_error_embed("Queue is full! Remove some tracks first.")
            )
            return
        
        # Start playback if not playing
        if not player.is_playing and not player.is_paused:
            await player.play()
        
        # Send response
        if len(tracks) == 1:
            track = tracks[0]
            if player.queue.size == 1:
                embed = create_track_embed(track, title="🎵 Now Playing")
            else:
                embed = create_track_embed(
                    track,
                    title="✅ Added to Queue",
                    position=player.queue.size - 1,
                )
        else:
            embed = create_success_embed(
                f"Added **{added}** tracks to the queue.\n"
                f"Queue now has **{player.queue.size}** tracks."
            )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="search", description="Search for a song and choose from results")
    @app_commands.describe(
        query="Search query",
        source="Search source (default: YouTube)"
    )
    @app_commands.choices(source=[
        app_commands.Choice(name="YouTube", value="youtube"),
        app_commands.Choice(name="SoundCloud", value="soundcloud"),
    ])
    @is_in_voice()
    @rate_limited()
    async def search(
        self,
        interaction: discord.Interaction,
        query: str,
        source: str = "youtube",
    ) -> None:
        """Search for tracks and display results."""
        await interaction.response.defer()
        
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        
        player = self.get_player(interaction.guild.id)
        
        # Search for tracks
        tracks = await player.extractor.search(
            query,
            interaction.user.id,
            interaction.user.display_name,
            limit=5,
            source=source,
        )
        
        if not tracks:
            await interaction.followup.send(
                embed=create_error_embed(f"No results found for: `{query}`")
            )
            return
        
        # Create search results embed with buttons
        embed = create_search_embed(tracks, query)
        view = SearchResultsView(tracks, player, interaction.user)
        
        await interaction.followup.send(embed=embed, view=view)
    
    # ==================== Playback Control ====================
    
    @app_commands.command(name="pause", description="Pause playback")
    @is_in_same_voice()
    @rate_limited()
    async def pause(self, interaction: discord.Interaction) -> None:
        """Pause current playback."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        
        if not player.is_playing:
            await interaction.response.send_message(
                embed=create_error_embed("Nothing is playing."),
                ephemeral=True,
            )
            return
        
        await player.pause()
        await interaction.response.send_message(
            embed=create_info_embed("⏸️ Playback paused.")
        )
    
    @app_commands.command(name="resume", description="Resume playback")
    @is_in_same_voice()
    @rate_limited()
    async def resume(self, interaction: discord.Interaction) -> None:
        """Resume paused playback."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        
        if not player.is_paused:
            await interaction.response.send_message(
                embed=create_error_embed("Playback is not paused."),
                ephemeral=True,
            )
            return
        
        await player.resume()
        await interaction.response.send_message(
            embed=create_info_embed("▶️ Playback resumed.")
        )
    
    @app_commands.command(name="skip", description="Skip to the next track")
    @is_in_same_voice()
    @rate_limited()
    async def skip(self, interaction: discord.Interaction) -> None:
        """Skip current track."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        
        if not player.current_track:
            await interaction.response.send_message(
                embed=create_error_embed("Nothing is playing."),
                ephemeral=True,
            )
            return
        
        skipped = player.current_track
        await player.skip()
        
        await interaction.response.send_message(
            embed=create_info_embed(f"⏭️ Skipped: **{skipped.display_title}**")
        )
    
    @app_commands.command(name="stop", description="Stop playback and clear the queue")
    @is_in_same_voice()
    @is_dj_or_admin()
    @rate_limited()
    async def stop(self, interaction: discord.Interaction) -> None:
        """Stop playback and clear queue."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        await player.stop()
        
        await interaction.response.send_message(
            embed=create_info_embed("⏹️ Playback stopped and queue cleared.")
        )
    
    @app_commands.command(name="seek", description="Seek to a position in the current track")
    @app_commands.describe(seconds="Position in seconds")
    @is_in_same_voice()
    @rate_limited()
    async def seek(self, interaction: discord.Interaction, seconds: int) -> None:
        """Seek to position in current track."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        
        if not player.current_track:
            await interaction.response.send_message(
                embed=create_error_embed("Nothing is playing."),
                ephemeral=True,
            )
            return
        
        await interaction.response.defer()
        
        success = await player.seek(seconds)
        
        if success:
            minutes, secs = divmod(seconds, 60)
            await interaction.followup.send(
                embed=create_info_embed(f"⏩ Seeked to **{minutes}:{secs:02d}**")
            )
        else:
            await interaction.followup.send(
                embed=create_error_embed("Failed to seek. Position may be invalid.")
            )
    
    @app_commands.command(name="volume", description="Set playback volume")
    @app_commands.describe(level="Volume level (0-200)")
    @is_in_same_voice()
    @rate_limited()
    async def volume(self, interaction: discord.Interaction, level: int) -> None:
        """Set volume level."""
        if not interaction.guild:
            return
        
        if not 0 <= level <= 200:
            await interaction.response.send_message(
                embed=create_error_embed("Volume must be between 0 and 200."),
                ephemeral=True,
            )
            return
        
        player = self.get_player(interaction.guild.id)
        player.volume = level
        
        # Volume emoji based on level
        if level == 0:
            emoji = "🔇"
        elif level < 50:
            emoji = "🔈"
        elif level < 100:
            emoji = "🔉"
        else:
            emoji = "🔊"
        
        await interaction.response.send_message(
            embed=create_info_embed(f"{emoji} Volume set to **{level}%**")
        )
    
    # ==================== Queue Management ====================
    
    @app_commands.command(name="queue", description="Show the current queue")
    @app_commands.describe(page="Page number")
    @rate_limited()
    async def queue(self, interaction: discord.Interaction, page: int = 1) -> None:
        """Display the queue."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        embed = create_queue_embed(player.queue, page=page - 1)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="now", description="Show the currently playing track")
    @rate_limited()
    async def now(self, interaction: discord.Interaction) -> None:
        """Show current track."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        track = player.current_track
        
        if not track:
            await interaction.response.send_message(
                embed=create_info_embed("Nothing is currently playing.")
            )
            return
        
        embed = create_track_embed(track)
        
        # Add playback status
        if player.is_paused:
            embed.add_field(name="Status", value="⏸️ Paused", inline=True)
        else:
            embed.add_field(name="Status", value="▶️ Playing", inline=True)
        
        embed.add_field(name="Volume", value=f"🔊 {player.volume}%", inline=True)
        embed.add_field(name="Loop", value=player.loop_mode.value.title(), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="remove", description="Remove a track from the queue")
    @app_commands.describe(position="Position in queue (1-based)")
    @is_in_same_voice()
    @rate_limited()
    async def remove(self, interaction: discord.Interaction, position: int) -> None:
        """Remove track from queue."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        
        # Convert to 0-based index
        index = position - 1
        
        if index < 0 or index >= player.queue.size:
            await interaction.response.send_message(
                embed=create_error_embed(f"Invalid position. Queue has {player.queue.size} tracks."),
                ephemeral=True,
            )
            return
        
        track = await player.remove_track(index)
        
        if track:
            await interaction.response.send_message(
                embed=create_success_embed(f"Removed: **{track.display_title}**")
            )
        else:
            await interaction.response.send_message(
                embed=create_error_embed("Failed to remove track."),
                ephemeral=True,
            )
    
    @app_commands.command(name="clear", description="Clear the queue (keeps current track)")
    @is_in_same_voice()
    @is_dj_or_admin()
    @rate_limited()
    async def clear(self, interaction: discord.Interaction) -> None:
        """Clear upcoming tracks."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        await player.clear_queue()
        
        await interaction.response.send_message(
            embed=create_success_embed("🗑️ Queue cleared.")
        )
    
    @app_commands.command(name="shuffle", description="Shuffle the queue")
    @is_in_same_voice()
    @rate_limited()
    async def shuffle(self, interaction: discord.Interaction) -> None:
        """Shuffle upcoming tracks."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        
        if player.queue.size <= 2:
            await interaction.response.send_message(
                embed=create_error_embed("Not enough tracks to shuffle."),
                ephemeral=True,
            )
            return
        
        player.shuffle()
        
        await interaction.response.send_message(
            embed=create_success_embed("🔀 Queue shuffled!")
        )
    
    @app_commands.command(name="loop", description="Set loop mode")
    @app_commands.describe(mode="Loop mode")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Off", value="off"),
        app_commands.Choice(name="One (repeat current)", value="one"),
        app_commands.Choice(name="All (repeat queue)", value="all"),
    ])
    @is_in_same_voice()
    @rate_limited()
    async def loop(self, interaction: discord.Interaction, mode: str) -> None:
        """Set loop mode."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        player.set_loop(LoopMode(mode))
        
        emoji = {"off": "➡️", "one": "🔂", "all": "🔁"}[mode]
        await interaction.response.send_message(
            embed=create_info_embed(f"{emoji} Loop mode: **{mode.title()}**")
        )
    
    # ==================== Voice Connection ====================
    
    @app_commands.command(name="join", description="Join your voice channel")
    @is_in_voice()
    @rate_limited()
    async def join(self, interaction: discord.Interaction) -> None:
        """Join voice channel."""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                embed=create_error_embed("You're not in a voice channel."),
                ephemeral=True,
            )
            return
        
        player = self.get_player(interaction.guild.id)
        channel = interaction.user.voice.channel
        
        connected = await player.connect(channel)
        
        if connected:
            await interaction.response.send_message(
                embed=create_success_embed(f"Joined {channel.mention}")
            )
        else:
            await interaction.response.send_message(
                embed=create_error_embed("Failed to join voice channel."),
                ephemeral=True,
            )
    
    @app_commands.command(name="leave", description="Leave the voice channel")
    @is_in_same_voice()
    @rate_limited()
    async def leave(self, interaction: discord.Interaction) -> None:
        """Leave voice channel."""
        if not interaction.guild:
            return
        
        player = self.get_player(interaction.guild.id)
        await player.disconnect()
        
        await interaction.response.send_message(
            embed=create_info_embed("👋 Disconnected from voice channel.")
        )


class SearchResultsView(discord.ui.View):
    """View with buttons for search results."""
    
    def __init__(
        self,
        tracks: list[Track],
        player: MusicPlayer,
        user: discord.User | discord.Member,
    ) -> None:
        super().__init__(timeout=60)
        self.tracks = tracks
        self.player = player
        self.user = user
        
        # Add buttons for each track
        for i, track in enumerate(tracks[:5], 1):
            button = discord.ui.Button(
                label=str(i),
                style=discord.ButtonStyle.primary,
                custom_id=f"search_{i}",
            )
            button.callback = self._make_callback(i - 1)
            self.add_item(button)
        
        # Cancel button
        cancel = discord.ui.Button(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="search_cancel",
        )
        cancel.callback = self._cancel_callback
        self.add_item(cancel)
    
    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message(
                    "This search was started by someone else.",
                    ephemeral=True,
                )
                return
            
            track = self.tracks[index]
            
            # Connect if needed
            if not self.player.is_connected:
                if isinstance(interaction.user, discord.Member):
                    if interaction.user.voice and interaction.user.voice.channel:
                        await self.player.connect(interaction.user.voice.channel)
            
            await self.player.add_track(track)
            
            if not self.player.is_playing:
                await self.player.play()
            
            embed = create_track_embed(track, title="✅ Added to Queue")
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        
        return callback
    
    async def _cancel_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This search was started by someone else.",
                ephemeral=True,
            )
            return
        
        await interaction.response.edit_message(
            embed=create_info_embed("Search cancelled."),
            view=None,
        )
        self.stop()
    
    async def on_timeout(self) -> None:
        """Handle view timeout."""
        pass  # Message will remain but buttons won't work


async def setup(bot: "MusicBot") -> None:
    """Setup function for loading the cog."""
    await bot.add_cog(MusicCog(bot))
