"""
Embed builders for consistent message formatting.
"""

from typing import Optional

import discord

from bot.music.track import Track
from bot.music.queue import MusicQueue, LoopMode


# Color scheme
COLOR_PRIMARY = 0x7289DA    # Discord blurple
COLOR_SUCCESS = 0x43B581    # Green
COLOR_WARNING = 0xFAA61A    # Yellow
COLOR_ERROR = 0xF04747      # Red
COLOR_INFO = 0x5865F2       # Blue


def create_track_embed(
    track: Track,
    title: str = "🎵 Now Playing",
    color: int = COLOR_PRIMARY,
    show_requester: bool = True,
    position: Optional[int] = None,
) -> discord.Embed:
    """
    Create embed for a track.
    
    Args:
        track: Track to display
        title: Embed title
        color: Embed color
        show_requester: Whether to show who requested the track
        position: Optional position in queue
    """
    embed = discord.Embed(
        title=title,
        description=f"**[{track.display_title}]({track.webpage_url or track.url})**",
        color=color,
    )
    
    # Duration
    embed.add_field(
        name="Duration",
        value=track.duration_str,
        inline=True,
    )
    
    # Source
    source_emoji = {
        "youtube": "🔴",
        "soundcloud": "🟠",
    }.get(track.source, "🎵")
    embed.add_field(
        name="Source",
        value=f"{source_emoji} {track.source.title()}",
        inline=True,
    )
    
    # Position in queue
    if position is not None:
        embed.add_field(
            name="Position",
            value=f"#{position + 1}",
            inline=True,
        )
    
    # Requester
    if show_requester:
        embed.set_footer(text=f"Requested by {track.requester_name}")
    
    # Thumbnail
    if track.thumbnail:
        embed.set_thumbnail(url=track.thumbnail)
    
    return embed


def create_queue_embed(
    queue: MusicQueue,
    page: int = 0,
    per_page: int = 10,
) -> discord.Embed:
    """
    Create embed for queue display.
    
    Args:
        queue: Music queue
        page: Page number (0-indexed)
        per_page: Tracks per page
    """
    embed = discord.Embed(
        title="📜 Music Queue",
        color=COLOR_INFO,
    )
    
    if queue.is_empty:
        embed.description = "The queue is empty. Use `/play` to add tracks!"
        return embed
    
    # Current track
    current = queue.current
    if current:
        embed.add_field(
            name="🎵 Now Playing",
            value=f"**[{current.display_title}]({current.webpage_url or current.url})** [{current.duration_str}]",
            inline=False,
        )
    
    # Upcoming tracks
    upcoming = queue.upcoming
    total_pages = max(1, (len(upcoming) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    
    start = page * per_page
    end = start + per_page
    page_tracks = upcoming[start:end]
    
    if page_tracks:
        lines = []
        for i, track in enumerate(page_tracks, start=start + 1):
            line = f"`{i}.` [{track.display_title}]({track.webpage_url or track.url}) [{track.duration_str}]"
            lines.append(line)
        
        embed.add_field(
            name=f"📋 Up Next ({len(upcoming)} tracks)",
            value="\n".join(lines),
            inline=False,
        )
    
    # Queue info
    loop_emoji = {
        LoopMode.OFF: "➡️",
        LoopMode.ONE: "🔂",
        LoopMode.ALL: "🔁",
    }[queue.loop_mode]
    
    # Total duration
    total_seconds = queue.total_duration
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        duration_str = f"{hours}h {minutes}m"
    else:
        duration_str = f"{minutes}m {seconds}s"
    
    embed.set_footer(
        text=f"Page {page + 1}/{total_pages} • {queue.size} tracks • {duration_str} • Loop: {loop_emoji}"
    )
    
    return embed


def create_search_embed(
    tracks: list[Track],
    query: str,
) -> discord.Embed:
    """
    Create embed for search results.
    
    Args:
        tracks: List of tracks found
        query: Original search query
    """
    embed = discord.Embed(
        title=f"🔍 Search Results for: {query}",
        color=COLOR_INFO,
    )
    
    if not tracks:
        embed.description = "No results found. Try a different search query."
        return embed
    
    lines = []
    for i, track in enumerate(tracks, 1):
        line = f"`{i}.` **{track.display_title}** [{track.duration_str}]"
        lines.append(line)
    
    embed.description = "\n".join(lines)
    embed.set_footer(text="Reply with a number to play, or 'cancel' to cancel")
    
    return embed


def create_error_embed(
    message: str,
    title: str = "❌ Error",
) -> discord.Embed:
    """Create error embed."""
    return discord.Embed(
        title=title,
        description=message,
        color=COLOR_ERROR,
    )


def create_success_embed(
    message: str,
    title: str = "✅ Success",
) -> discord.Embed:
    """Create success embed."""
    return discord.Embed(
        title=title,
        description=message,
        color=COLOR_SUCCESS,
    )


def create_info_embed(
    message: str,
    title: str = "ℹ️ Info",
) -> discord.Embed:
    """Create info embed."""
    return discord.Embed(
        title=title,
        description=message,
        color=COLOR_INFO,
    )
