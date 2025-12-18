"""
Track model representing a playable audio track.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Track:
    """
    Represents a single audio track.
    
    Attributes:
        url: Original URL or search query
        title: Track title
        duration: Duration in seconds
        thumbnail: Thumbnail URL
        webpage_url: URL to the track's webpage
        stream_url: Direct stream URL (may expire)
        source: Source platform (youtube, soundcloud, etc.)
        requester_id: Discord user ID who requested the track
        requester_name: Discord username who requested the track
        added_at: Timestamp when track was added to queue
    """
    
    url: str
    title: str = "Unknown Title"
    duration: int = 0
    thumbnail: Optional[str] = None
    webpage_url: Optional[str] = None
    stream_url: Optional[str] = None
    source: str = "unknown"
    requester_id: Optional[int] = None
    requester_name: str = "Unknown"
    added_at: datetime = field(default_factory=datetime.now)
    
    @property
    def duration_str(self) -> str:
        """Format duration as HH:MM:SS or MM:SS."""
        if self.duration <= 0:
            return "Live"
        
        hours, remainder = divmod(self.duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    
    @property
    def display_title(self) -> str:
        """Get display title, truncated if too long."""
        max_len = 60
        if len(self.title) > max_len:
            return self.title[:max_len - 3] + "..."
        return self.title
    
    def to_dict(self) -> dict[str, Any]:
        """Convert track to dictionary for serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "webpage_url": self.webpage_url,
            "source": self.source,
            "requester_id": self.requester_id,
            "requester_name": self.requester_name,
            # Note: stream_url is not persisted as it expires
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Track":
        """Create track from dictionary."""
        return cls(
            url=data.get("url", ""),
            title=data.get("title", "Unknown Title"),
            duration=data.get("duration", 0),
            thumbnail=data.get("thumbnail"),
            webpage_url=data.get("webpage_url"),
            source=data.get("source", "unknown"),
            requester_id=data.get("requester_id"),
            requester_name=data.get("requester_name", "Unknown"),
        )
    
    @classmethod
    def from_ytdlp(cls, info: dict[str, Any], requester_id: int, requester_name: str) -> "Track":
        """
        Create track from yt-dlp extracted info.
        
        Args:
            info: yt-dlp info dictionary
            requester_id: Discord user ID
            requester_name: Discord username
        """
        # Determine source from extractor
        extractor = info.get("extractor", "").lower()
        if "youtube" in extractor:
            source = "youtube"
        elif "soundcloud" in extractor:
            source = "soundcloud"
        else:
            source = extractor or "unknown"
        
        return cls(
            url=info.get("original_url") or info.get("webpage_url") or info.get("url", ""),
            title=info.get("title", "Unknown Title"),
            duration=int(info.get("duration") or 0),
            thumbnail=info.get("thumbnail"),
            webpage_url=info.get("webpage_url"),
            stream_url=info.get("url"),  # Direct stream URL
            source=source,
            requester_id=requester_id,
            requester_name=requester_name,
        )
