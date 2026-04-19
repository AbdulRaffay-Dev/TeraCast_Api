"""Rate limiter to prevent API abuse."""
import time
from functools import wraps
from typing import Dict, List
from flask import request, jsonify
from config import RATE_LIMIT, RATE_WINDOW


class RateLimiter:
    """
    Sliding window rate limiter.
    
    Tracks requests per IP address and limits them to a maximum
    number within a time window.
    """
    
    def __init__(self, max_requests: int = RATE_LIMIT, window_seconds: int = RATE_WINDOW):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self._requests: Dict[str, List[float]] = {}
        self._max_requests = max_requests
        self._window_seconds = window_seconds
    
    def is_allowed(self, ip: str) -> bool:
        """
        Check if request is allowed for this IP.
        
        Args:
            ip: Client IP address
            
        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()
        window_start = current_time - self._window_seconds
        
        # Initialize request history for new IPs
        if ip not in self._requests:
            self._requests[ip] = []
        
        # Remove old requests outside the current window
        self._requests[ip] = [
            req_time for req_time in self._requests[ip]
            if req_time > window_start
        ]
        
        # Check if under the limit
        if len(self._requests[ip]) >= self._max_requests:
            return False
        
        # Record this request
        self._requests[ip].append(current_time)
        return True
    
    def get_retry_after(self, ip: str) -> int:
        """
        Get seconds until rate limit resets.
        
        Args:
            ip: Client IP address
            
        Returns:
            Seconds to wait before retrying
        """
        if ip not in self._requests or not self._requests[ip]:
            return 0
        
        oldest_request = min(self._requests[ip])
        retry_after = int(oldest_request + self._window_seconds - time.time())
        return max(0, retry_after)


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(f):
    """
    Decorator to apply rate limiting to Flask routes.
    
    Returns 429 Too Many Requests if limit exceeded.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get client IP (check X-Forwarded-For for proxies)
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # Check rate limit
        if not rate_limiter.is_allowed(ip):
            retry_after = rate_limiter.get_retry_after(ip)
            return jsonify({
                "status": "error",
                "message": "Rate limit exceeded. Please slow down.",
                "retry_after_seconds": retry_after,
                "error_code": "RATE_LIMITED"
            }), 429
        
        # Call the original function
        return f(*args, **kwargs)
    
    return decorated_function
