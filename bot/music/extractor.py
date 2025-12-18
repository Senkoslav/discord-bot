"""
Audio extraction using yt-dlp.
Handles YouTube, SoundCloud, and other supported sources.
"""

import asyncio
import logging
import re
from typing import Any, Optional

import yt_dlp

from bot.music.track import Track

logger = logging.getLogger(__name__)

# yt-dlp options for audio extraction
YTDLP_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": False,  # Allow playlists
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",  # Default to YouTube search
    "source_address": "0.0.0.0",   # Bind to IPv4
    "extract_flat": False,
    "geo_bypass": True,
    # Don't download, just extract info
    "skip_download": True,
}

# FFmpeg options for streaming
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",  # No video
}

# URL patterns
YOUTUBE_REGEX = re.compile(
    r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+"
)
SOUNDCLOUD_REGEX = re.compile(
    r"(https?://)?(www\.)?soundcloud\.com/.+"
)
URL_REGEX = re.compile(
    r"https?://[^\s]+"
)


class AudioExtractor:
    """
    Extracts audio information from URLs or search queries.
    
    Uses yt-dlp to support multiple platforms:
    - YouTube (URLs and search)
    - SoundCloud (URLs and search)
    - Many other platforms supported by yt-dlp
    """
    
    def __init__(self, cookies_path: Optional[str] = None) -> None:
        """
        Initialize extractor.
        
        Args:
            cookies_path: Optional path to cookies file for age-restricted content
        """
        self._options = YTDLP_OPTIONS.copy()
        if cookies_path:
            self._options["cookiefile"] = cookies_path
    
    @staticmethod
    def is_url(query: str) -> bool:
        """Check if query is a URL."""
        return bool(URL_REGEX.match(query.strip()))
    
    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """Check if URL is a YouTube URL."""
        return bool(YOUTUBE_REGEX.match(url.strip()))
    
    @staticmethod
    def is_soundcloud_url(url: str) -> bool:
        """Check if URL is a SoundCloud URL."""
        return bool(SOUNDCLOUD_REGEX.match(url.strip()))
    
    @staticmethod
    def is_playlist_url(url: str) -> bool:
        """Check if URL is a playlist URL."""
        return "playlist" in url.lower() or "list=" in url
    
    async def extract(
        self,
        query: str,
        requester_id: int,
        requester_name: str,
        search_limit: int = 1,
    ) -> list[Track]:
        """
        Extract track(s) from URL or search query.
        
        Args:
            query: URL or search query
            requester_id: Discord user ID
            requester_name: Discord username
            search_limit: Max results for search queries
        
        Returns:
            List of Track objects
        """
        query = query.strip()
        
        # Determine search prefix if not a URL
        if not self.is_url(query):
            # Use YouTube search by default
            query = f"ytsearch{search_limit}:{query}"
        
        try:
            # Run extraction in thread pool (yt-dlp is blocking)
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: self._extract_info(query)
            )
            
            if not info:
                return []
            
            return self._process_info(info, requester_id, requester_name)
            
        except Exception as e:
            logger.error("Extraction failed for '%s': %s", query, e)
            return []
    
    async def search(
        self,
        query: str,
        requester_id: int,
        requester_name: str,
        limit: int = 5,
        source: str = "youtube",
    ) -> list[Track]:
        """
        Search for tracks.
        
        Args:
            query: Search query
            requester_id: Discord user ID
            requester_name: Discord username
            limit: Max results
            source: Search source (youtube, soundcloud)
        
        Returns:
            List of Track objects
        """
        if source == "soundcloud":
            search_query = f"scsearch{limit}:{query}"
        else:
            search_query = f"ytsearch{limit}:{query}"
        
        return await self.extract(search_query, requester_id, requester_name, limit)
    
    async def get_stream_url(self, track: Track) -> Optional[str]:
        """
        Get fresh stream URL for a track.
        
        Stream URLs can expire, so this refreshes them before playback.
        
        Args:
            track: Track to get stream URL for
        
        Returns:
            Stream URL or None if extraction fails
        """
        url = track.webpage_url or track.url
        
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: self._extract_info(url)
            )
            
            if info and "url" in info:
                return info["url"]
            
            # Handle playlist/search results
            if info and "entries" in info:
                entries = [e for e in info["entries"] if e]
                if entries:
                    return entries[0].get("url")
            
            return None
            
        except Exception as e:
            logger.error("Failed to get stream URL for '%s': %s", track.title, e)
            return None
    
    def _extract_info(self, query: str) -> Optional[dict[str, Any]]:
        """
        Extract info using yt-dlp (blocking).
        
        This runs in a thread pool.
        """
        try:
            with yt_dlp.YoutubeDL(self._options) as ydl:
                return ydl.extract_info(query, download=False)
        except Exception as e:
            logger.error("yt-dlp extraction error: %s", e)
            return None
    
    def _process_info(
        self,
        info: dict[str, Any],
        requester_id: int,
        requester_name: str,
    ) -> list[Track]:
        """Process yt-dlp info dict into Track objects."""
        tracks = []
        
        # Handle playlist/search results
        if "entries" in info:
            entries = [e for e in info.get("entries", []) if e]
            for entry in entries:
                try:
                    track = Track.from_ytdlp(entry, requester_id, requester_name)
                    tracks.append(track)
                except Exception as e:
                    logger.warning("Failed to process entry: %s", e)
        else:
            # Single track
            try:
                track = Track.from_ytdlp(info, requester_id, requester_name)
                tracks.append(track)
            except Exception as e:
                logger.warning("Failed to process track: %s", e)
        
        return tracks


# FFmpeg audio source options
def get_ffmpeg_options() -> dict[str, str]:
    """Get FFmpeg options for audio streaming."""
    return FFMPEG_OPTIONS.copy()
