"""
Database manager with Redis/SQLite fallback support.
Handles queue persistence and user playlists.
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import aiosqlite

if TYPE_CHECKING:
    from bot.core.config import Config
    from bot.music.track import Track

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages data persistence with Redis or SQLite fallback.
    
    Provides methods for:
    - Queue persistence (save/restore between restarts)
    - User playlists
    - Guild settings
    """
    
    def __init__(self, config: "Config") -> None:
        """Initialize database manager."""
        self.config = config
        self._redis: Optional[Any] = None
        self._sqlite: Optional[aiosqlite.Connection] = None
        self._use_redis = config.use_redis
    
    async def initialize(self) -> None:
        """Initialize database connection."""
        if self._use_redis:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(
                    self.config.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # Test connection
                await self._redis.ping()
                logger.info("Connected to Redis")
                return
            except Exception as e:
                logger.warning("Redis connection failed, falling back to SQLite: %s", e)
                self._use_redis = False
        
        # SQLite fallback
        db_path = Path(self.config.sqlite_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._sqlite = await aiosqlite.connect(str(db_path))
        await self._create_tables()
        logger.info("Connected to SQLite: %s", db_path)
    
    async def _create_tables(self) -> None:
        """Create SQLite tables if they don't exist."""
        if not self._sqlite:
            return
        
        await self._sqlite.executescript("""
            CREATE TABLE IF NOT EXISTS guild_queues (
                guild_id INTEGER PRIMARY KEY,
                queue_data TEXT NOT NULL,
                current_index INTEGER DEFAULT 0,
                loop_mode TEXT DEFAULT 'off',
                volume INTEGER DEFAULT 100,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS user_playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                tracks TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            );
            
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                dj_role_id INTEGER,
                default_volume INTEGER DEFAULT 100,
                max_queue_size INTEGER DEFAULT 500,
                announce_tracks INTEGER DEFAULT 1
            );
            
            CREATE INDEX IF NOT EXISTS idx_playlists_user ON user_playlists(user_id);
        """)
        await self._sqlite.commit()
    
    async def close(self) -> None:
        """Close database connections."""
        if self._redis:
            await self._redis.close()
        if self._sqlite:
            await self._sqlite.close()
    
    # Queue persistence methods
    
    async def save_queue(
        self,
        guild_id: int,
        tracks: list["Track"],
        current_index: int = 0,
        loop_mode: str = "off",
        volume: int = 100,
    ) -> None:
        """Save guild queue to database."""
        queue_data = json.dumps([t.to_dict() for t in tracks])
        
        if self._use_redis and self._redis:
            key = f"queue:{guild_id}"
            await self._redis.hset(key, mapping={
                "queue_data": queue_data,
                "current_index": str(current_index),
                "loop_mode": loop_mode,
                "volume": str(volume),
            })
            await self._redis.expire(key, 86400 * 7)  # 7 days TTL
        elif self._sqlite:
            await self._sqlite.execute("""
                INSERT OR REPLACE INTO guild_queues 
                (guild_id, queue_data, current_index, loop_mode, volume, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (guild_id, queue_data, current_index, loop_mode, volume))
            await self._sqlite.commit()
    
    async def load_queue(self, guild_id: int) -> Optional[dict]:
        """Load guild queue from database."""
        if self._use_redis and self._redis:
            key = f"queue:{guild_id}"
            data = await self._redis.hgetall(key)
            if data:
                return {
                    "tracks": json.loads(data.get("queue_data", "[]")),
                    "current_index": int(data.get("current_index", 0)),
                    "loop_mode": data.get("loop_mode", "off"),
                    "volume": int(data.get("volume", 100)),
                }
        elif self._sqlite:
            async with self._sqlite.execute(
                "SELECT queue_data, current_index, loop_mode, volume FROM guild_queues WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "tracks": json.loads(row[0]),
                        "current_index": row[1],
                        "loop_mode": row[2],
                        "volume": row[3],
                    }
        return None
    
    async def clear_guild_queue(self, guild_id: int) -> None:
        """Clear guild queue from database."""
        if self._use_redis and self._redis:
            await self._redis.delete(f"queue:{guild_id}")
        elif self._sqlite:
            await self._sqlite.execute(
                "DELETE FROM guild_queues WHERE guild_id = ?", (guild_id,)
            )
            await self._sqlite.commit()
    
    # User playlist methods
    
    async def save_playlist(
        self, user_id: int, name: str, tracks: list["Track"]
    ) -> bool:
        """Save user playlist."""
        tracks_data = json.dumps([t.to_dict() for t in tracks])
        
        try:
            if self._use_redis and self._redis:
                key = f"playlist:{user_id}:{name}"
                await self._redis.set(key, tracks_data)
            elif self._sqlite:
                await self._sqlite.execute("""
                    INSERT OR REPLACE INTO user_playlists (user_id, name, tracks)
                    VALUES (?, ?, ?)
                """, (user_id, name, tracks_data))
                await self._sqlite.commit()
            return True
        except Exception as e:
            logger.error("Failed to save playlist: %s", e)
            return False
    
    async def load_playlist(self, user_id: int, name: str) -> Optional[list[dict]]:
        """Load user playlist."""
        if self._use_redis and self._redis:
            key = f"playlist:{user_id}:{name}"
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
        elif self._sqlite:
            async with self._sqlite.execute(
                "SELECT tracks FROM user_playlists WHERE user_id = ? AND name = ?",
                (user_id, name)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
        return None
    
    async def list_playlists(self, user_id: int) -> list[str]:
        """List user's playlist names."""
        if self._use_redis and self._redis:
            pattern = f"playlist:{user_id}:*"
            keys = await self._redis.keys(pattern)
            return [k.split(":")[-1] for k in keys]
        elif self._sqlite:
            async with self._sqlite.execute(
                "SELECT name FROM user_playlists WHERE user_id = ?", (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
        return []
    
    async def delete_playlist(self, user_id: int, name: str) -> bool:
        """Delete user playlist."""
        try:
            if self._use_redis and self._redis:
                key = f"playlist:{user_id}:{name}"
                await self._redis.delete(key)
            elif self._sqlite:
                await self._sqlite.execute(
                    "DELETE FROM user_playlists WHERE user_id = ? AND name = ?",
                    (user_id, name)
                )
                await self._sqlite.commit()
            return True
        except Exception as e:
            logger.error("Failed to delete playlist: %s", e)
            return False
