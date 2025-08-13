"""Advanced caching manager for web scraping results and data."""

import os
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
import sqlite3
import threading
from dataclasses import asdict

from models.product_data import ProductData
from models.processing_result import ScrapingResult
from utils.logger import get_logger


class CacheManager:
    """Advanced cache manager with multiple storage backends."""
    
    def __init__(self, cache_dir: str = "cache", max_age_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.max_age_hours = max_age_hours
        self.logger = get_logger(__name__)
        
        # Create cache directory and subdirectories
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "data").mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite database for metadata
        self.db_path = self.cache_dir / "cache_metadata.db"
        self.lock = threading.RLock()
        self._init_database()
        
        self.logger.info(f"Cache manager initialized: {self.cache_dir} (TTL: {max_age_hours}h)")
    
    def _init_database(self):
        """Initialize SQLite database for cache metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    url_hash TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    cached_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    file_path TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    extraction_method TEXT,
                    data_confidence REAL,
                    file_size INTEGER
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_url ON cache_entries(url)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)
            """)
            
            conn.commit()
    
    def _get_url_hash(self, url: str) -> str:
        """Generate a hash for the URL to use as cache key."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()
    
    def _get_cache_file_path(self, url_hash: str) -> Path:
        """Get the file path for cached data."""
        # Organize cache files in subdirectories to avoid too many files in one directory
        subdir = url_hash[:2]
        cache_subdir = self.cache_dir / "data" / subdir
        cache_subdir.mkdir(parents=True, exist_ok=True)
        return cache_subdir / f"{url_hash}.pkl"
    
    def is_cached(self, url: str) -> bool:
        """Check if URL result is cached and not expired."""
        url_hash = self._get_url_hash(url)
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT expires_at FROM cache_entries WHERE url_hash = ?",
                        (url_hash,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        expires_at = datetime.fromisoformat(row[0])
                        is_valid = expires_at > datetime.now()
                        
                        if not is_valid:
                            # Clean up expired entry
                            self._remove_cache_entry(url_hash)
                        
                        return is_valid
                    
                    return False
                    
            except Exception as e:
                self.logger.warning(f"Error checking cache for {url}: {e}")
                return False
    
    def get_cached_result(self, url: str) -> Optional[ScrapingResult]:
        """Retrieve cached scraping result for URL."""
        if not self.is_cached(url):
            return None
        
        url_hash = self._get_url_hash(url)
        cache_file = self._get_cache_file_path(url_hash)
        
        with self.lock:
            try:
                if cache_file.exists():
                    with open(cache_file, 'rb') as f:
                        cached_result = pickle.load(f)
                    
                    self.logger.debug(f"Cache hit for {url}")
                    return cached_result
                else:
                    # File missing, clean up database entry
                    self._remove_cache_entry(url_hash)
                    return None
                    
            except Exception as e:
                self.logger.warning(f"Error reading cache for {url}: {e}")
                # Clean up corrupted cache entry
                self._remove_cache_entry(url_hash)
                return None
    
    def cache_result(self, url: str, result: ScrapingResult):
        """Cache a scraping result."""
        url_hash = self._get_url_hash(url)
        cache_file = self._get_cache_file_path(url_hash)
        
        with self.lock:
            try:
                # Save the result to file
                with open(cache_file, 'wb') as f:
                    pickle.dump(result, f)
                
                # Update database metadata
                cached_at = datetime.now()
                expires_at = cached_at + timedelta(hours=self.max_age_hours)
                file_size = cache_file.stat().st_size
                
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO cache_entries 
                        (url_hash, url, cached_at, expires_at, file_path, success, 
                         extraction_method, data_confidence, file_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        url_hash, url, cached_at.isoformat(), expires_at.isoformat(),
                        str(cache_file), result.status.name == 'COMPLETED',
                        result.extraction_method or '', 
                        getattr(result.data, 'extraction_confidence', 0.0) if result.data else 0.0,
                        file_size
                    ))
                    conn.commit()
                
                self.logger.debug(f"Cached result for {url} (expires: {expires_at})")
                
            except Exception as e:
                self.logger.error(f"Error caching result for {url}: {e}")
                # Clean up partial cache entry
                if cache_file.exists():
                    cache_file.unlink()
    
    def _remove_cache_entry(self, url_hash: str):
        """Remove cache entry and associated file."""
        try:
            cache_file = self._get_cache_file_path(url_hash)
            if cache_file.exists():
                cache_file.unlink()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM cache_entries WHERE url_hash = ?", (url_hash,))
                conn.commit()
                
        except Exception as e:
            self.logger.warning(f"Error removing cache entry {url_hash}: {e}")
    
    def cleanup_expired(self) -> int:
        """Clean up expired cache entries and return count of removed entries."""
        removed_count = 0
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Find expired entries
                    cursor = conn.execute(
                        "SELECT url_hash, file_path FROM cache_entries WHERE expires_at < ?",
                        (datetime.now().isoformat(),)
                    )
                    expired_entries = cursor.fetchall()
                    
                    for url_hash, file_path in expired_entries:
                        # Remove file
                        cache_file = Path(file_path)
                        if cache_file.exists():
                            cache_file.unlink()
                        
                        # Remove database entry
                        conn.execute("DELETE FROM cache_entries WHERE url_hash = ?", (url_hash,))
                        removed_count += 1
                    
                    conn.commit()
                    
            except Exception as e:
                self.logger.error(f"Error during cache cleanup: {e}")
        
        if removed_count > 0:
            self.logger.info(f"Cleaned up {removed_count} expired cache entries")
        
        return removed_count
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache usage statistics."""
        stats = {
            "total_entries": 0,
            "successful_entries": 0,
            "failed_entries": 0,
            "total_size_mb": 0.0,
            "oldest_entry": None,
            "newest_entry": None,
            "cache_hit_potential": 0.0
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Count entries
                cursor = conn.execute("SELECT COUNT(*), SUM(file_size) FROM cache_entries")
                total_count, total_size = cursor.fetchone()
                
                stats["total_entries"] = total_count or 0
                stats["total_size_mb"] = (total_size or 0) / (1024 * 1024)
                
                # Count successful vs failed
                cursor = conn.execute("SELECT success, COUNT(*) FROM cache_entries GROUP BY success")
                for success, count in cursor.fetchall():
                    if success:
                        stats["successful_entries"] = count
                    else:
                        stats["failed_entries"] = count
                
                # Get date range
                cursor = conn.execute("SELECT MIN(cached_at), MAX(cached_at) FROM cache_entries")
                oldest, newest = cursor.fetchone()
                
                if oldest:
                    stats["oldest_entry"] = oldest
                if newest:
                    stats["newest_entry"] = newest
                
                # Calculate potential cache hit rate (successful entries / total)
                if stats["total_entries"] > 0:
                    stats["cache_hit_potential"] = (stats["successful_entries"] / stats["total_entries"]) * 100
                    
        except Exception as e:
            self.logger.error(f"Error getting cache statistics: {e}")
        
        return stats
    
    def clear_cache(self, older_than_hours: Optional[int] = None):
        """Clear cache entries, optionally only those older than specified hours."""
        removed_count = 0
        
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    if older_than_hours:
                        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
                        cursor = conn.execute(
                            "SELECT url_hash, file_path FROM cache_entries WHERE cached_at < ?",
                            (cutoff_time.isoformat(),)
                        )
                    else:
                        cursor = conn.execute("SELECT url_hash, file_path FROM cache_entries")
                    
                    entries_to_remove = cursor.fetchall()
                    
                    for url_hash, file_path in entries_to_remove:
                        # Remove file
                        cache_file = Path(file_path)
                        if cache_file.exists():
                            cache_file.unlink()
                        
                        removed_count += 1
                    
                    # Clear database entries
                    if older_than_hours:
                        conn.execute(
                            "DELETE FROM cache_entries WHERE cached_at < ?",
                            (cutoff_time.isoformat(),)
                        )
                    else:
                        conn.execute("DELETE FROM cache_entries")
                    
                    conn.commit()
                    
            except Exception as e:
                self.logger.error(f"Error clearing cache: {e}")
        
        self.logger.info(f"Cleared {removed_count} cache entries")
        return removed_count


class MemoryCache:
    """In-memory cache for frequently accessed data with LRU eviction."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order: List[str] = []
        self.lock = threading.RLock()
        self.logger = get_logger(f"{__name__}.memory")
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from memory cache."""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                
                entry = self.cache[key]
                
                # Check if expired
                if entry['expires_at'] > datetime.now():
                    return entry['data']
                else:
                    # Remove expired entry
                    del self.cache[key]
                    self.access_order.remove(key)
            
            return None
    
    def put(self, key: str, data: Any, ttl_seconds: int = 300):
        """Store item in memory cache with TTL."""
        with self.lock:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            
            # Remove existing entry if present
            if key in self.cache:
                self.access_order.remove(key)
            
            # Add new entry
            self.cache[key] = {
                'data': data,
                'expires_at': expires_at,
                'cached_at': datetime.now()
            }
            self.access_order.append(key)
            
            # Evict least recently used items if cache is full
            while len(self.cache) > self.max_size:
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]
    
    def clear(self):
        """Clear all items from memory cache."""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory cache statistics."""
        with self.lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "utilization": (len(self.cache) / self.max_size) * 100 if self.max_size > 0 else 0
            }