"""
Rate limiting utilities for Telegram API requests.

Implements adaptive rate limiting to avoid hitting Telegram API limits
and prevent account restrictions.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

from loguru import logger


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    
    # Maximum requests per window
    max_requests: int = 20
    
    # Time window in seconds
    window_seconds: float = 60.0
    
    # Minimum delay between requests (seconds)
    min_delay: float = 1.0
    
    # Maximum delay between requests (seconds)
    max_delay: float = 10.0
    
    # Exponential backoff multiplier when approaching limits
    backoff_multiplier: float = 1.5


@dataclass
class RateLimiter:
    """
    Adaptive rate limiter for Telegram API requests.
    
    Features:
    - Sliding window rate limiting
    - Exponential backoff when approaching limits
    - Automatic cooldown on errors
    - Human-like request patterns
    """
    
    config: RateLimitConfig = field(default_factory=RateLimitConfig)
    
    # Request timestamps (sliding window)
    _requests: Deque[float] = field(default_factory=deque)
    
    # Current delay between requests
    _current_delay: float = field(init=False)
    
    # Lock for thread-safe operations
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    # Cooldown until timestamp (for error recovery)
    _cooldown_until: Optional[float] = None
    
    def __post_init__(self):
        """Initialize current delay."""
        self._current_delay = self.config.min_delay
    
    async def acquire(self) -> None:
        """
        Acquire permission to make a request.
        
        This method will wait if necessary to respect rate limits.
        """
        async with self._lock:
            # Check cooldown
            if self._cooldown_until is not None:
                wait_time = self._cooldown_until - time.time()
                if wait_time > 0:
                    logger.warning(
                        f"Rate limiter in cooldown, waiting {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                self._cooldown_until = None
            
            # Clean old requests outside window
            now = time.time()
            cutoff = now - self.config.window_seconds
            
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            
            # Check if we're at the limit
            if len(self._requests) >= self.config.max_requests:
                # Calculate wait time until oldest request expires
                oldest = self._requests[0]
                wait_time = self.config.window_seconds - (now - oldest)
                
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached ({len(self._requests)}/{self.config.max_requests}), "
                        f"waiting {wait_time:.1f}s"
                    )
                    await asyncio.sleep(wait_time)
                    
                    # Clean up again after waiting
                    now = time.time()
                    cutoff = now - self.config.window_seconds
                    while self._requests and self._requests[0] < cutoff:
                        self._requests.popleft()
            
            # Calculate adaptive delay based on usage
            usage_ratio = len(self._requests) / self.config.max_requests
            
            if usage_ratio > 0.8:
                # Approaching limit - increase delay exponentially
                self._current_delay = min(
                    self._current_delay * self.config.backoff_multiplier,
                    self.config.max_delay
                )
            elif usage_ratio < 0.5:
                # Low usage - decrease delay
                self._current_delay = max(
                    self._current_delay / self.config.backoff_multiplier,
                    self.config.min_delay
                )
            
            # Add jitter to make requests more human-like
            jitter = self._current_delay * 0.2  # ±20% jitter
            import random
            delay = self._current_delay + random.uniform(-jitter, jitter)
            delay = max(self.config.min_delay, delay)
            
            # Wait before request
            if self._requests:  # Not the first request
                await asyncio.sleep(delay)
            
            # Record request
            self._requests.append(time.time())
            
            logger.debug(
                f"Rate limiter: {len(self._requests)}/{self.config.max_requests} requests, "
                f"delay: {delay:.2f}s"
            )
    
    async def report_error(self, error: Exception) -> None:
        """
        Report an error that may be rate-limit related.
        
        This will trigger a cooldown period.
        
        Args:
            error: The error that occurred
        """
        async with self._lock:
            # Determine cooldown duration based on error type
            cooldown_seconds = 60.0  # Default 1 minute
            
            error_str = str(error).lower()
            
            if "flood" in error_str or "too many" in error_str:
                # Flood wait - longer cooldown
                cooldown_seconds = 300.0  # 5 minutes
                logger.error(
                    f"Flood wait detected: {error}. "
                    f"Cooling down for {cooldown_seconds}s"
                )
            elif "timeout" in error_str:
                cooldown_seconds = 30.0  # 30 seconds
                logger.warning(f"Timeout error: {error}. Cooling down for {cooldown_seconds}s")
            else:
                logger.warning(f"API error: {error}. Cooling down for {cooldown_seconds}s")
            
            self._cooldown_until = time.time() + cooldown_seconds
            
            # Reset delay to maximum
            self._current_delay = self.config.max_delay
    
    def reset(self) -> None:
        """Reset rate limiter state."""
        self._requests.clear()
        self._current_delay = self.config.min_delay
        self._cooldown_until = None
        logger.info("Rate limiter reset")
    
    @property
    def current_usage(self) -> tuple[int, int]:
        """
        Get current usage.
        
        Returns:
            Tuple of (current_requests, max_requests)
        """
        # Clean old requests
        now = time.time()
        cutoff = now - self.config.window_seconds
        
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()
        
        return (len(self._requests), self.config.max_requests)


class GlobalRateLimiter:
    """
    Global rate limiter singleton for sharing across multiple services.
    """
    
    _instance: Optional[RateLimiter] = None
    
    @classmethod
    def get_instance(cls, config: Optional[RateLimitConfig] = None) -> RateLimiter:
        """
        Get or create global rate limiter instance.
        
        Args:
            config: Optional configuration (only used on first call)
        
        Returns:
            RateLimiter instance
        """
        if cls._instance is None:
            if config is None:
                config = RateLimitConfig()
            cls._instance = RateLimiter(config=config)
        
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset global instance."""
        if cls._instance:
            cls._instance.reset()
        cls._instance = None


__all__ = [
    "RateLimitConfig",
    "RateLimiter",
    "GlobalRateLimiter",
]


