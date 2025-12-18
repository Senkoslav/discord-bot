"""
Music queue management for guild-scoped playback.
"""

import random
from enum import Enum
from typing import Optional

from bot.music.track import Track


class LoopMode(Enum):
    """Loop mode options."""
    OFF = "off"
    ONE = "one"      # Repeat current track
    ALL = "all"      # Repeat entire queue


class MusicQueue:
    """
    Guild-scoped music queue with loop and shuffle support.
    
    Manages the track list, current position, and playback modes.
    """
    
    def __init__(self, max_size: int = 500) -> None:
        """
        Initialize empty queue.
        
        Args:
            max_size: Maximum number of tracks allowed in queue
        """
        self._tracks: list[Track] = []
        self._current_index: int = 0
        self._loop_mode: LoopMode = LoopMode.OFF
        self._max_size = max_size
        self._history: list[Track] = []  # Recently played tracks
    
    @property
    def tracks(self) -> list[Track]:
        """Get all tracks in queue."""
        return self._tracks.copy()
    
    @property
    def current(self) -> Optional[Track]:
        """Get current track."""
        if 0 <= self._current_index < len(self._tracks):
            return self._tracks[self._current_index]
        return None
    
    @property
    def current_index(self) -> int:
        """Get current track index."""
        return self._current_index
    
    @property
    def loop_mode(self) -> LoopMode:
        """Get current loop mode."""
        return self._loop_mode
    
    @loop_mode.setter
    def loop_mode(self, mode: LoopMode) -> None:
        """Set loop mode."""
        self._loop_mode = mode
    
    @property
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._tracks) == 0
    
    @property
    def size(self) -> int:
        """Get number of tracks in queue."""
        return len(self._tracks)
    
    @property
    def upcoming(self) -> list[Track]:
        """Get upcoming tracks (after current)."""
        if self._current_index + 1 < len(self._tracks):
            return self._tracks[self._current_index + 1:]
        return []
    
    @property
    def total_duration(self) -> int:
        """Get total duration of all tracks in seconds."""
        return sum(t.duration for t in self._tracks)
    
    def add(self, track: Track) -> bool:
        """
        Add track to end of queue.
        
        Returns:
            True if added, False if queue is full
        """
        if len(self._tracks) >= self._max_size:
            return False
        self._tracks.append(track)
        return True
    
    def add_many(self, tracks: list[Track]) -> int:
        """
        Add multiple tracks to queue.
        
        Returns:
            Number of tracks actually added
        """
        available = self._max_size - len(self._tracks)
        to_add = tracks[:available]
        self._tracks.extend(to_add)
        return len(to_add)
    
    def insert(self, index: int, track: Track) -> bool:
        """Insert track at specific position."""
        if len(self._tracks) >= self._max_size:
            return False
        
        # Adjust index to be after current if needed
        actual_index = max(self._current_index + 1, min(index, len(self._tracks)))
        self._tracks.insert(actual_index, track)
        return True
    
    def remove(self, index: int) -> Optional[Track]:
        """
        Remove track at index.
        
        Returns:
            Removed track or None if invalid index
        """
        if not 0 <= index < len(self._tracks):
            return None
        
        track = self._tracks.pop(index)
        
        # Adjust current index if needed
        if index < self._current_index:
            self._current_index -= 1
        elif index == self._current_index and self._current_index >= len(self._tracks):
            self._current_index = max(0, len(self._tracks) - 1)
        
        return track
    
    def clear(self) -> None:
        """Clear all tracks from queue."""
        self._tracks.clear()
        self._current_index = 0
    
    def clear_upcoming(self) -> int:
        """
        Clear upcoming tracks (keep current and history).
        
        Returns:
            Number of tracks removed
        """
        if self._current_index + 1 < len(self._tracks):
            removed = len(self._tracks) - self._current_index - 1
            self._tracks = self._tracks[:self._current_index + 1]
            return removed
        return 0
    
    def next(self) -> Optional[Track]:
        """
        Advance to next track based on loop mode.
        
        Returns:
            Next track or None if queue ended
        """
        if self.is_empty:
            return None
        
        # Add current to history
        if self.current:
            self._history.append(self.current)
            if len(self._history) > 50:  # Keep last 50 tracks
                self._history.pop(0)
        
        if self._loop_mode == LoopMode.ONE:
            # Stay on current track
            return self.current
        
        if self._current_index + 1 < len(self._tracks):
            # Move to next track
            self._current_index += 1
            return self.current
        
        if self._loop_mode == LoopMode.ALL:
            # Loop back to start
            self._current_index = 0
            return self.current
        
        # Queue ended
        return None
    
    def previous(self) -> Optional[Track]:
        """
        Go to previous track.
        
        Returns:
            Previous track or None
        """
        if self._current_index > 0:
            self._current_index -= 1
            return self.current
        
        if self._loop_mode == LoopMode.ALL and len(self._tracks) > 0:
            self._current_index = len(self._tracks) - 1
            return self.current
        
        return None
    
    def jump(self, index: int) -> Optional[Track]:
        """
        Jump to specific track index.
        
        Returns:
            Track at index or None if invalid
        """
        if 0 <= index < len(self._tracks):
            self._current_index = index
            return self.current
        return None
    
    def shuffle(self) -> None:
        """Shuffle upcoming tracks (keep current track in place)."""
        if self._current_index + 1 < len(self._tracks):
            upcoming = self._tracks[self._current_index + 1:]
            random.shuffle(upcoming)
            self._tracks = self._tracks[:self._current_index + 1] + upcoming
    
    def move(self, from_index: int, to_index: int) -> bool:
        """
        Move track from one position to another.
        
        Returns:
            True if successful
        """
        if not (0 <= from_index < len(self._tracks) and 0 <= to_index < len(self._tracks)):
            return False
        
        track = self._tracks.pop(from_index)
        self._tracks.insert(to_index, track)
        
        # Adjust current index
        if from_index == self._current_index:
            self._current_index = to_index
        elif from_index < self._current_index <= to_index:
            self._current_index -= 1
        elif to_index <= self._current_index < from_index:
            self._current_index += 1
        
        return True
    
    def get_state(self) -> dict:
        """Get queue state for persistence."""
        return {
            "tracks": self._tracks,
            "current_index": self._current_index,
            "loop_mode": self._loop_mode.value,
        }
    
    def restore_state(
        self,
        tracks: list[Track],
        current_index: int = 0,
        loop_mode: str = "off",
    ) -> None:
        """Restore queue state from persistence."""
        self._tracks = tracks
        self._current_index = min(current_index, max(0, len(tracks) - 1))
        self._loop_mode = LoopMode(loop_mode)
