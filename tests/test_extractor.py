"""
Tests for the AudioExtractor class.
"""

import pytest

from bot.music.extractor import AudioExtractor


class TestAudioExtractor:
    """Tests for AudioExtractor URL detection."""
    
    def test_is_url_valid(self):
        """Test URL detection for valid URLs."""
        assert AudioExtractor.is_url("https://youtube.com/watch?v=test")
        assert AudioExtractor.is_url("http://example.com")
        assert AudioExtractor.is_url("https://soundcloud.com/artist/track")
    
    def test_is_url_invalid(self):
        """Test URL detection for non-URLs."""
        assert not AudioExtractor.is_url("hello world")
        assert not AudioExtractor.is_url("search query")
        assert not AudioExtractor.is_url("youtube video")
    
    def test_is_youtube_url(self):
        """Test YouTube URL detection."""
        assert AudioExtractor.is_youtube_url("https://youtube.com/watch?v=test")
        assert AudioExtractor.is_youtube_url("https://www.youtube.com/watch?v=test")
        assert AudioExtractor.is_youtube_url("https://youtu.be/test")
        assert AudioExtractor.is_youtube_url("http://youtube.com/playlist?list=test")
    
    def test_is_youtube_url_invalid(self):
        """Test YouTube URL detection for non-YouTube URLs."""
        assert not AudioExtractor.is_youtube_url("https://soundcloud.com/test")
        assert not AudioExtractor.is_youtube_url("https://example.com")
        assert not AudioExtractor.is_youtube_url("youtube video search")
    
    def test_is_soundcloud_url(self):
        """Test SoundCloud URL detection."""
        assert AudioExtractor.is_soundcloud_url("https://soundcloud.com/artist/track")
        assert AudioExtractor.is_soundcloud_url("https://www.soundcloud.com/artist/track")
        assert AudioExtractor.is_soundcloud_url("http://soundcloud.com/sets/playlist")
    
    def test_is_soundcloud_url_invalid(self):
        """Test SoundCloud URL detection for non-SoundCloud URLs."""
        assert not AudioExtractor.is_soundcloud_url("https://youtube.com/test")
        assert not AudioExtractor.is_soundcloud_url("soundcloud track")
    
    def test_is_playlist_url(self):
        """Test playlist URL detection."""
        assert AudioExtractor.is_playlist_url("https://youtube.com/playlist?list=test")
        assert AudioExtractor.is_playlist_url("https://youtube.com/watch?v=test&list=abc")
        assert AudioExtractor.is_playlist_url("https://soundcloud.com/artist/sets/playlist")
    
    def test_is_playlist_url_invalid(self):
        """Test playlist URL detection for non-playlist URLs."""
        assert not AudioExtractor.is_playlist_url("https://youtube.com/watch?v=test")
        assert not AudioExtractor.is_playlist_url("https://soundcloud.com/artist/track")


# Integration tests (require network, skip in CI)
@pytest.mark.skip(reason="Requires network access")
class TestAudioExtractorIntegration:
    """Integration tests for AudioExtractor (require network)."""
    
    @pytest.mark.asyncio
    async def test_extract_youtube_url(self):
        """Test extracting from YouTube URL."""
        extractor = AudioExtractor()
        tracks = await extractor.extract(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            123,
            "TestUser",
        )
        
        assert len(tracks) == 1
        assert tracks[0].source == "youtube"
        assert tracks[0].title  # Should have a title
    
    @pytest.mark.asyncio
    async def test_search_youtube(self):
        """Test YouTube search."""
        extractor = AudioExtractor()
        tracks = await extractor.search(
            "never gonna give you up",
            123,
            "TestUser",
            limit=3,
        )
        
        assert len(tracks) <= 3
        assert all(t.source == "youtube" for t in tracks)
