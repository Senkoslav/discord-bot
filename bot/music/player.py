"""
Music player for guild voice channels.
Handles audio streaming, playback control, and queue management.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Callable, Optional

import discord

from bot.music.extractor import AudioExtractor, get_ffmpeg_options
from bot.music.queue import LoopMode, MusicQueue
from bot.music.track import Track

if TYPE_CHECKING:
    from bot.core.config import Config
    from bot.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class MusicPlayer:
    """
    Guild-scoped music player.
    
    Manages voice connection, audio streaming, and playback state.
    Each guild has its own player instance.
    """
    
    def __init__(
        self,
        guild_id: int,
        config: "Config",
        db: Optional["DatabaseManager"] = None,
    ) -> None:
        """
        Initialize player for a guild.
        
        Args:
            guild_id: Discord guild ID
            config: Bot configuration
            db: Database manager for persistence
        """
        self.guild_id = guild_id
        self.config = config
        self.db = db
        
        self.queue = MusicQueue(max_size=config.max_queue_size)
        self.extractor = AudioExtractor(cookies_path=config.youtube_cookies_path)
        
        self._voice_client: Optional[discord.VoiceClient] = None
        self._volume: float = config.default_volume / 100
        self._is_playing: bool = False
        self._current_position: float = 0  # Seconds into current track
        self._paused: bool = False
        
        # Callbacks
        self._on_track_start: Optional[Callable[[Track], None]] = None
        self._on_track_end: Optional[Callable[[Track], None]] = None
        self._on_queue_end: Optional[Callable[[], None]] = None
        
        # Inactivity tracking
        self._inactivity_task: Optional[asyncio.Task] = None
        self._last_activity: float = 0
    
    @property
    def voice_client(self) -> Optional[discord.VoiceClient]:
        """Get current voice client."""
        return self._voice_client
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to voice."""
        return self._voice_client is not None and self._voice_client.is_connected()
    
    @property
    def is_playing(self) -> bool:
        """Check if currently playing audio."""
        return self._is_playing and not self._paused
    
    @property
    def is_paused(self) -> bool:
        """Check if playback is paused."""
        return self._paused
    
    @property
    def volume(self) -> int:
        """Get current volume (0-200)."""
        return int(self._volume * 100)
    
    @volume.setter
    def volume(self, value: int) -> None:
        """Set volume (0-200)."""
        self._volume = max(0, min(200, value)) / 100
        
        # Update current audio source volume
        if self._voice_client and self._voice_client.source:
            if isinstance(self._voice_client.source, discord.PCMVolumeTransformer):
                self._voice_client.source.volume = self._volume
    
    @property
    def current_track(self) -> Optional[Track]:
        """Get currently playing track."""
        return self.queue.current
    
    @property
    def loop_mode(self) -> LoopMode:
        """Get current loop mode."""
        return self.queue.loop_mode
    
    async def connect(self, channel: discord.VoiceChannel) -> bool:
        """
        Connect to voice channel.
        
        Args:
            channel: Voice channel to connect to
        
        Returns:
            True if connected successfully
        """
        try:
            if self._voice_client:
                if self._voice_client.channel == channel:
                    return True
                await self._voice_client.move_to(channel)
            else:
                self._voice_client = await channel.connect(
                    timeout=10.0,
                    reconnect=True,
                )
            
            logger.info("Connected to voice channel: %s", channel.name)
            self._start_inactivity_timer()
            return True
            
        except Exception as e:
            logger.error("Failed to connect to voice: %s", e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from voice channel."""
        self._stop_inactivity_timer()
        
        if self._voice_client:
            try:
                self._voice_client.stop()
                await self._voice_client.disconnect(force=True)
            except Exception as e:
                logger.warning("Error disconnecting: %s", e)
            finally:
                self._voice_client = None
                self._is_playing = False
                self._paused = False
        
        # Save queue state
        await self._save_state()
    
    async def play(self, track: Optional[Track] = None) -> bool:
        """
        Start or resume playback.
        
        Args:
            track: Optional track to play immediately
        
        Returns:
            True if playback started
        """
        if not self.is_connected:
            return False
        
        # If track provided, add to front of queue
        if track:
            self.queue.insert(self.queue.current_index, track)
        
        # Resume if paused
        if self._paused and self._voice_client:
            self._voice_client.resume()
            self._paused = False
            return True
        
        # Start playing current track
        return await self._play_current()
    
    async def _play_current(self) -> bool:
        """Play the current track in queue."""
        track = self.queue.current
        if not track:
            self._is_playing = False
            if self._on_queue_end:
                self._on_queue_end()
            return False
        
        if not self._voice_client:
            return False
        
        try:
            # Get fresh stream URL
            stream_url = await self.extractor.get_stream_url(track)
            if not stream_url:
                logger.warning("Failed to get stream URL for: %s", track.title)
                # Skip to next track
                await self.skip()
                return False
            
            # Create audio source with FFmpeg
            ffmpeg_opts = get_ffmpeg_options()
            source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_opts)
            
            # Wrap with volume transformer
            source = discord.PCMVolumeTransformer(source, volume=self._volume)
            
            # Stop current playback if any
            if self._voice_client.is_playing():
                self._voice_client.stop()
            
            # Start playback
            self._voice_client.play(
                source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self._on_playback_end(e),
                    asyncio.get_event_loop(),
                ),
            )
            
            self._is_playing = True
            self._paused = False
            self._current_position = 0
            self._reset_inactivity()
            
            logger.info("Now playing: %s", track.title)
            
            if self._on_track_start:
                self._on_track_start(track)
            
            return True
            
        except Exception as e:
            logger.error("Playback error: %s", e)
            self._is_playing = False
            # Try next track
            await self.skip()
            return False
    
    async def _on_playback_end(self, error: Optional[Exception]) -> None:
        """Handle playback end event."""
        if error:
            logger.error("Playback error: %s", error)
        
        old_track = self.queue.current
        
        if self._on_track_end and old_track:
            self._on_track_end(old_track)
        
        # Move to next track
        next_track = self.queue.next()
        
        if next_track:
            await self._play_current()
        else:
            self._is_playing = False
            if self._on_queue_end:
                self._on_queue_end()
            await self._save_state()
    
    async def pause(self) -> bool:
        """Pause playback."""
        if self._voice_client and self._voice_client.is_playing():
            self._voice_client.pause()
            self._paused = True
            return True
        return False
    
    async def resume(self) -> bool:
        """Resume playback."""
        if self._voice_client and self._paused:
            self._voice_client.resume()
            self._paused = False
            return True
        return False
    
    async def stop(self) -> None:
        """Stop playback and clear queue."""
        if self._voice_client:
            self._voice_client.stop()
        
        self.queue.clear()
        self._is_playing = False
        self._paused = False
        
        await self._save_state()
    
    async def skip(self) -> Optional[Track]:
        """
        Skip to next track.
        
        Returns:
            Next track or None if queue ended
        """
        if self._voice_client and self._voice_client.is_playing():
            self._voice_client.stop()
            # _on_playback_end will handle moving to next track
        else:
            # Manually advance if not playing
            next_track = self.queue.next()
            if next_track:
                await self._play_current()
            return next_track
        
        return self.queue.current
    
    async def seek(self, seconds: int) -> bool:
        """
        Seek to position in current track.
        
        Note: This restarts the stream at the new position.
        
        Args:
            seconds: Position in seconds
        
        Returns:
            True if seek successful
        """
        track = self.queue.current
        if not track or not self._voice_client:
            return False
        
        if seconds < 0 or (track.duration > 0 and seconds >= track.duration):
            return False
        
        try:
            stream_url = await self.extractor.get_stream_url(track)
            if not stream_url:
                return False
            
            # Stop current playback
            self._voice_client.stop()
            
            # Create new source with seek position
            ffmpeg_opts = get_ffmpeg_options()
            ffmpeg_opts["before_options"] = (
                f"-ss {seconds} " + ffmpeg_opts.get("before_options", "")
            )
            
            source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_opts)
            source = discord.PCMVolumeTransformer(source, volume=self._volume)
            
            self._voice_client.play(
                source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self._on_playback_end(e),
                    asyncio.get_event_loop(),
                ),
            )
            
            self._current_position = seconds
            return True
            
        except Exception as e:
            logger.error("Seek error: %s", e)
            return False
    
    def set_loop(self, mode: LoopMode) -> None:
        """Set loop mode."""
        self.queue.loop_mode = mode
    
    def shuffle(self) -> None:
        """Shuffle upcoming tracks."""
        self.queue.shuffle()
    
    async def add_track(self, track: Track) -> bool:
        """Add track to queue."""
        result = self.queue.add(track)
        if result:
            await self._save_state()
        return result
    
    async def add_tracks(self, tracks: list[Track]) -> int:
        """Add multiple tracks to queue."""
        count = self.queue.add_many(tracks)
        if count > 0:
            await self._save_state()
        return count
    
    async def remove_track(self, index: int) -> Optional[Track]:
        """Remove track at index."""
        track = self.queue.remove(index)
        if track:
            await self._save_state()
        return track
    
    async def clear_queue(self) -> None:
        """Clear the queue (keep current track)."""
        self.queue.clear_upcoming()
        await self._save_state()
    
    # Persistence
    
    async def _save_state(self) -> None:
        """Save queue state to database."""
        if self.db:
            try:
                await self.db.save_queue(
                    self.guild_id,
                    self.queue.tracks,
                    self.queue.current_index,
                    self.queue.loop_mode.value,
                    self.volume,
                )
            except Exception as e:
                logger.error("Failed to save queue state: %s", e)
    
    async def restore_state(self) -> bool:
        """Restore queue state from database."""
        if not self.db:
            return False
        
        try:
            data = await self.db.load_queue(self.guild_id)
            if data:
                tracks = [Track.from_dict(t) for t in data["tracks"]]
                self.queue.restore_state(
                    tracks,
                    data["current_index"],
                    data["loop_mode"],
                )
                self.volume = data["volume"]
                logger.info("Restored queue for guild %s: %d tracks", self.guild_id, len(tracks))
                return True
        except Exception as e:
            logger.error("Failed to restore queue state: %s", e)
        
        return False
    
    # Inactivity handling
    
    def _start_inactivity_timer(self) -> None:
        """Start inactivity disconnect timer."""
        self._stop_inactivity_timer()
        self._reset_inactivity()
        self._inactivity_task = asyncio.create_task(self._inactivity_check())
    
    def _stop_inactivity_timer(self) -> None:
        """Stop inactivity timer."""
        if self._inactivity_task:
            self._inactivity_task.cancel()
            self._inactivity_task = None
    
    def _reset_inactivity(self) -> None:
        """Reset inactivity timer."""
        import time
        self._last_activity = time.time()
    
    async def _inactivity_check(self) -> None:
        """Check for inactivity and disconnect if needed."""
        import time
        
        while True:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            if not self.is_connected:
                break
            
            # Don't disconnect if playing
            if self.is_playing:
                self._reset_inactivity()
                continue
            
            elapsed = time.time() - self._last_activity
            if elapsed >= self.config.inactivity_timeout:
                logger.info("Disconnecting due to inactivity (guild: %s)", self.guild_id)
                await self.disconnect()
                break
    
    # Callbacks
    
    def on_track_start(self, callback: Callable[[Track], None]) -> None:
        """Set callback for track start."""
        self._on_track_start = callback
    
    def on_track_end(self, callback: Callable[[Track], None]) -> None:
        """Set callback for track end."""
        self._on_track_end = callback
    
    def on_queue_end(self, callback: Callable[[], None]) -> None:
        """Set callback for queue end."""
        self._on_queue_end = callback
