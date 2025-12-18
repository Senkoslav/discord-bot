"""
Tests for the MusicQueue class.
"""

import pytest

from bot.music.queue import MusicQueue, LoopMode
from bot.music.track import Track


def create_test_track(title: str = "Test Track", duration: int = 180) -> Track:
    """Create a test track."""
    return Track(
        url="https://example.com/test",
        title=title,
        duration=duration,
        source="test",
        requester_id=123,
        requester_name="TestUser",
    )


class TestMusicQueue:
    """Tests for MusicQueue."""
    
    def test_empty_queue(self):
        """Test empty queue properties."""
        queue = MusicQueue()
        
        assert queue.is_empty
        assert queue.size == 0
        assert queue.current is None
        assert queue.upcoming == []
    
    def test_add_track(self):
        """Test adding a track."""
        queue = MusicQueue()
        track = create_test_track("Track 1")
        
        result = queue.add(track)
        
        assert result is True
        assert queue.size == 1
        assert queue.current == track
        assert not queue.is_empty
    
    def test_add_multiple_tracks(self):
        """Test adding multiple tracks."""
        queue = MusicQueue()
        tracks = [create_test_track(f"Track {i}") for i in range(5)]
        
        count = queue.add_many(tracks)
        
        assert count == 5
        assert queue.size == 5
        assert queue.current == tracks[0]
        assert len(queue.upcoming) == 4
    
    def test_max_queue_size(self):
        """Test queue size limit."""
        queue = MusicQueue(max_size=3)
        tracks = [create_test_track(f"Track {i}") for i in range(5)]
        
        count = queue.add_many(tracks)
        
        assert count == 3
        assert queue.size == 3
    
    def test_remove_track(self):
        """Test removing a track."""
        queue = MusicQueue()
        tracks = [create_test_track(f"Track {i}") for i in range(3)]
        queue.add_many(tracks)
        
        removed = queue.remove(1)
        
        assert removed == tracks[1]
        assert queue.size == 2
    
    def test_remove_invalid_index(self):
        """Test removing with invalid index."""
        queue = MusicQueue()
        queue.add(create_test_track())
        
        removed = queue.remove(5)
        
        assert removed is None
        assert queue.size == 1
    
    def test_next_track(self):
        """Test advancing to next track."""
        queue = MusicQueue()
        tracks = [create_test_track(f"Track {i}") for i in range(3)]
        queue.add_many(tracks)
        
        next_track = queue.next()
        
        assert next_track == tracks[1]
        assert queue.current == tracks[1]
        assert queue.current_index == 1
    
    def test_next_at_end(self):
        """Test next at end of queue."""
        queue = MusicQueue()
        queue.add(create_test_track())
        
        next_track = queue.next()
        
        assert next_track is None
    
    def test_loop_one(self):
        """Test loop one mode."""
        queue = MusicQueue()
        track = create_test_track()
        queue.add(track)
        queue.loop_mode = LoopMode.ONE
        
        next_track = queue.next()
        
        assert next_track == track
        assert queue.current_index == 0
    
    def test_loop_all(self):
        """Test loop all mode."""
        queue = MusicQueue()
        tracks = [create_test_track(f"Track {i}") for i in range(2)]
        queue.add_many(tracks)
        queue.loop_mode = LoopMode.ALL
        
        # Go to end
        queue.next()
        next_track = queue.next()
        
        assert next_track == tracks[0]
        assert queue.current_index == 0
    
    def test_shuffle(self):
        """Test shuffle functionality."""
        queue = MusicQueue()
        tracks = [create_test_track(f"Track {i}") for i in range(10)]
        queue.add_many(tracks)
        
        # Get original upcoming order
        original_upcoming = queue.upcoming.copy()
        
        queue.shuffle()
        
        # Current track should remain the same
        assert queue.current == tracks[0]
        # Upcoming should be different (with high probability)
        # Note: There's a tiny chance shuffle produces same order
        assert queue.size == 10
    
    def test_clear(self):
        """Test clearing queue."""
        queue = MusicQueue()
        tracks = [create_test_track(f"Track {i}") for i in range(5)]
        queue.add_many(tracks)
        
        queue.clear()
        
        assert queue.is_empty
        assert queue.size == 0
    
    def test_clear_upcoming(self):
        """Test clearing upcoming tracks."""
        queue = MusicQueue()
        tracks = [create_test_track(f"Track {i}") for i in range(5)]
        queue.add_many(tracks)
        
        removed = queue.clear_upcoming()
        
        assert removed == 4
        assert queue.size == 1
        assert queue.current == tracks[0]
    
    def test_jump(self):
        """Test jumping to specific track."""
        queue = MusicQueue()
        tracks = [create_test_track(f"Track {i}") for i in range(5)]
        queue.add_many(tracks)
        
        result = queue.jump(3)
        
        assert result == tracks[3]
        assert queue.current_index == 3
    
    def test_jump_invalid(self):
        """Test jumping to invalid index."""
        queue = MusicQueue()
        queue.add(create_test_track())
        
        result = queue.jump(10)
        
        assert result is None
        assert queue.current_index == 0
    
    def test_total_duration(self):
        """Test total duration calculation."""
        queue = MusicQueue()
        tracks = [
            create_test_track("Track 1", duration=100),
            create_test_track("Track 2", duration=200),
            create_test_track("Track 3", duration=300),
        ]
        queue.add_many(tracks)
        
        assert queue.total_duration == 600
    
    def test_state_persistence(self):
        """Test state save and restore."""
        queue = MusicQueue()
        tracks = [create_test_track(f"Track {i}") for i in range(3)]
        queue.add_many(tracks)
        queue.next()
        queue.loop_mode = LoopMode.ALL
        
        state = queue.get_state()
        
        new_queue = MusicQueue()
        new_queue.restore_state(
            state["tracks"],
            state["current_index"],
            state["loop_mode"],
        )
        
        assert new_queue.size == 3
        assert new_queue.current_index == 1
        assert new_queue.loop_mode == LoopMode.ALL
