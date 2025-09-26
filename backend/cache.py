"""Caching system for performance optimization."""
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from functools import wraps

from flask import current_app


class CacheManager:
    """Simple in-memory cache manager."""
    
    def __init__(self):
        self.cache = {}
        self.default_ttl = 300  # 5 minutes
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if datetime.utcnow() > entry['expires_at']:
            del self.cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        self.cache[key] = {
            'value': value,
            'expires_at': expires_at,
            'created_at': datetime.utcnow()
        }
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache."""
        self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now > entry['expires_at']
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        now = datetime.utcnow()
        active_entries = sum(
            1 for entry in self.cache.values()
            if now <= entry['expires_at']
        )
        
        return {
            'total_keys': len(self.cache),
            'active_entries': active_entries,
            'expired_entries': len(self.cache) - active_entries
        }


# Global cache manager
cache_manager = CacheManager()


def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_invalidate(pattern: str):
    """Invalidate cache entries matching pattern."""
    keys_to_delete = [key for key in cache_manager.cache.keys() if pattern in key]
    for key in keys_to_delete:
        cache_manager.delete(key)
    return len(keys_to_delete)


class QueryOptimizer:
    """Database query optimization utilities."""
    
    @staticmethod
    def optimize_pagination_query(query, page: int, per_page: int):
        """Optimize pagination queries."""
        # Use offset and limit efficiently
        offset = (page - 1) * per_page
        return query.offset(offset).limit(per_page)
    
    @staticmethod
    def add_eager_loading(query, relationships: list):
        """Add eager loading for relationships to avoid N+1 queries."""
        from sqlalchemy.orm import joinedload
        
        for relationship in relationships:
            query = query.options(joinedload(relationship))
        
        return query
    
    @staticmethod
    def add_indexes_hints(query, indexes: list):
        """Add database index hints for better performance."""
        # This would be database-specific implementation
        return query


class APIOptimizer:
    """API response optimization utilities."""
    
    @staticmethod
    def compress_response(data: dict) -> dict:
        """Compress API response by removing unnecessary fields."""
        # Remove None values and empty strings
        compressed = {}
        for key, value in data.items():
            if value is not None and value != "":
                if isinstance(value, dict):
                    compressed_value = APIOptimizer.compress_response(value)
                    if compressed_value:
                        compressed[key] = compressed_value
                elif isinstance(value, list) and value:
                    compressed[key] = value
                elif not isinstance(value, (dict, list)):
                    compressed[key] = value
        
        return compressed
    
    @staticmethod
    def paginate_response(data: list, page: int, per_page: int, total: int) -> dict:
        """Create optimized paginated response."""
        return {
            'data': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_next': page * per_page < total,
                'has_prev': page > 1
            }
        }


# Performance monitoring
class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.metrics = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'db_queries': 0,
            'avg_response_time': 0
        }
    
    def record_api_call(self, response_time: float):
        """Record API call metrics."""
        self.metrics['api_calls'] += 1
        # Update average response time
        total_calls = self.metrics['api_calls']
        current_avg = self.metrics['avg_response_time']
        self.metrics['avg_response_time'] = (
            (current_avg * (total_calls - 1) + response_time) / total_calls
        )
    
    def record_cache_hit(self):
        """Record cache hit."""
        self.metrics['cache_hits'] += 1
    
    def record_cache_miss(self):
        """Record cache miss."""
        self.metrics['cache_misses'] += 1
    
    def record_db_query(self):
        """Record database query."""
        self.metrics['db_queries'] += 1
    
    def get_metrics(self) -> dict:
        """Get performance metrics."""
        cache_hit_rate = 0
        if self.metrics['cache_hits'] + self.metrics['cache_misses'] > 0:
            cache_hit_rate = (
                self.metrics['cache_hits'] / 
                (self.metrics['cache_hits'] + self.metrics['cache_misses'])
            ) * 100
        
        return {
            **self.metrics,
            'cache_hit_rate': f"{cache_hit_rate:.2f}%"
        }


# Global performance monitor
performance_monitor = PerformanceMonitor()
