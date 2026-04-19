"""Simple in-memory cache with TTL (Time To Live)."""
import time
from typing import Any, Dict, Optional
from dataclasses import dataclass
from config import CACHE_TTL, CACHE_MAX_SIZE


@dataclass
class CacheEntry:
    """Represents a single cache entry with value and expiration time."""
    value: Any
    expires_at: float  # Unix timestamp when this entry expires


class SimpleCache:
    """
    LRU (Least Recently Used) cache with TTL support.
    
    This cache automatically expires entries after a set time
    and removes oldest entries when max size is reached.
    """
    
    def __init__(self, ttl: int = CACHE_TTL, max_size: int = CACHE_MAX_SIZE):
        """
        Initialize cache.
        
        Args:
            ttl: Time to live in seconds
            max_size: Maximum number of entries to keep
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._ttl = ttl
        self._max_size = max_size
    
    def get(self, key: str, password: str = "") -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key (usually the URL)
            password: Optional password for password-protected links
            
        Returns:
            Cached value or None if not found/expired
        """
        # Create unique cache key
        cache_key = f"{key}:{password}" if password else key
        
        # Get entry
        entry = self._cache.get(cache_key)
        if entry is None:
            return None
        
        # Check if expired
        if time.time() > entry.expires_at:
            # Remove expired entry
            self._cache.pop(cache_key, None)
            return None
        
        return entry.value
    
    def put(self, key: str, value: Any, password: str = "") -> None:
        """
        Put value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            password: Optional password for password-protected links
        """
        cache_key = f"{key}:{password}" if password else key
        
        # Remove oldest entry if at max size
        if len(self._cache) >= self._max_size:
            # Get the oldest key (first inserted)
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key)
        
        # Add new entry
        self._cache[cache_key] = CacheEntry(
            value=value,
            expires_at=time.time() + self._ttl
        )
    
    def clear(self) -> None:
        """Clear all entries from cache."""
        self._cache.clear()
    
    def size(self) -> int:
        """Get current number of entries in cache."""
        return len(self._cache)


# Global cache instance (singleton)
cache = SimpleCache()
