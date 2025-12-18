"""
Tests for the Track class.
"""

import pytest

from bot.music.track import Track


class TestTrack:
    """Tests for Track model."""
    
    def test_track_creation(self):
        """Test basic track creation."""
        track = Track(
            url="https://youtube.com/watch?v=test",
            title="Test Song",
            duration=180,
            source="youtube",
            requester_id=123,
            requester_name="TestUser",
        )
        
        assert track.url == "https://youtube.com/watch?v=test"
        assert track.title == "Test Song"
        assert track.duration == 180
        assert track.source == "youtube"
    
    def test_duration_str_minutes(self):
        """Test duration formatting for minutes."""
        track = Track(url="test", duration=185)
        
        assert track.duration_str == "3:05"
    
    def test_duration_str_hours(self):
        """Test duration formatting for hours."""
        track = Track(url="test", duration=3665)
        
        assert track.duration_str == "1:01:05"
    
    def test_duration_str_live(self):
        """Test duration formatting for live streams."""
        track = Track(url="test", duration=0)
        
        assert track.duration_str == "Live"
    
    def test_display_title_short(self):
        """Test display title for short titles."""
        track = Track(url="test", title="Short Title")
        
        assert track.display_title == "Short Title"
    
    def test_display_title_long(self):
        """Test display title truncation for long titles."""
        long_title = "A" * 100
        track = Track(url="test", title=long_title)
        
        assert len(track.display_title) == 60
        assert track.display_title.endswith("...")
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        track = Track(
            url="https://example.com",
            title="Test",
            duration=100,
            thumbnail="https://example.com/thumb.jpg",
            webpage_url="https://example.com/page",
            source="youtube",
            requester_id=123,
            requester_name="User",
        )
        
        data = track.to_dict()
        
        assert data["url"] == "https://example.com"
        assert data["title"] == "Test"
        assert data["duration"] == 100
        assert data["source"] == "youtube"
        assert "stream_url" not in data  # Should not be persisted
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "url": "https://example.com",
            "title": "Test Track",
            "duration": 200,
            "source": "soundcloud",
            "requester_id": 456,
            "requester_name": "AnotherUser",
        }
        
        track = Track.from_dict(data)
        
        assert track.url == "https://example.com"
        assert track.title == "Test Track"
        assert track.duration == 200
        assert track.source == "soundcloud"
    
    def test_from_dict_defaults(self):
        """Test deserialization with missing fields."""
        data = {"url": "https://example.com"}
        
        track = Track.from_dict(data)
        
        assert track.url == "https://example.com"
        assert track.title == "Unknown Title"
        assert track.duration == 0
        assert track.source == "unknown"
    
    def test_from_ytdlp(self):
        """Test creation from yt-dlp info dict."""
        info = {
            "title": "YouTube Video",
            "duration": 300,
            "thumbnail": "https://i.ytimg.com/test.jpg",
            "webpage_url": "https://youtube.com/watch?v=test",
            "url": "https://stream.url/audio",
            "extractor": "youtube",
            "original_url": "https://youtube.com/watch?v=test",
        }
        
        track = Track.from_ytdlp(info, 789, "YouTubeUser")
        
        assert track.title == "YouTube Video"
        assert track.duration == 300
        assert track.source == "youtube"
        assert track.stream_url == "https://stream.url/audio"
        assert track.requester_id == 789
        assert track.requester_name == "YouTubeUser"
    
    def test_from_ytdlp_soundcloud(self):
        """Test source detection for SoundCloud."""
        info = {
            "title": "SoundCloud Track",
            "extractor": "soundcloud",
            "url": "https://stream.url",
        }
        
        track = Track.from_ytdlp(info, 1, "User")
        
        assert track.source == "soundcloud"
