"""
Smart caching manager for Stock Signal Brief.
Caches fetched web pages, RSS feeds, and YouTube transcripts with SHA256 hashes and TTL.
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cache_manager")

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_FILE = CACHE_DIR / "sources_cache.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Default cache Time-To-Live: 12 hours (43200 seconds)
DEFAULT_TTL_SECONDS = 43200


class SmartCacheManager:
    """Manages persistent JSON caching for fetched web pages and media transcripts."""

    def __init__(self, cache_file: Path = CACHE_FILE, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.cache_file = cache_file
        self.ttl = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = self._load_cache()
        self.hits = 0
        self.misses = 0

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cache file: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache file: {e}")

    def _hash_key(self, key_string: str) -> str:
        return hashlib.sha256(key_string.encode("utf-8")).hexdigest()

    def get(self, key_string: str) -> Optional[Any]:
        """Returns cached payload if present and not expired."""
        h_key = self._hash_key(key_string)
        entry = self._cache.get(h_key)

        if entry:
            cached_time = entry.get("cached_at", 0)
            if time.time() - cached_time < self.ttl:
                self.hits += 1
                logger.info(f"[CACHE HIT] Reusing cached entry for '{key_string[:50]}...'")
                return entry.get("payload")
            else:
                # Expired
                del self._cache[h_key]
                self._save_cache()

        self.misses += 1
        return None

    def set(self, key_string: str, payload: Any):
        """Saves payload to cache with timestamp."""
        h_key = self._hash_key(key_string)
        self._cache[h_key] = {
            "key": key_string,
            "cached_at": time.time(),
            "payload": payload
        }
        self._save_cache()
        logger.info(f"[CACHE STORED] Saved entry for '{key_string[:50]}...'")

    def get_stats(self) -> Dict[str, Any]:
        """Returns cache efficiency metrics."""
        total_queries = self.hits + self.misses
        hit_rate = (self.hits / total_queries * 100.0) if total_queries > 0 else 0.0
        return {
            "total_cached_entries": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percentage": round(hit_rate, 1),
            "ttl_hours": round(self.ttl / 3600, 1)
        }


# Global instance
smart_cache = SmartCacheManager()
