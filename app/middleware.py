"""
Middleware for production security and rate limiting
"""
import time
import logging
from typing import Dict, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict, deque
import asyncio

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent abuse
    """
    
    def __init__(self, app, requests_per_minute: int = 60, burst_limit: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.burst_requests: Dict[str, deque] = defaultdict(deque)
        self.cleanup_interval = 60  # Clean up every minute
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean up old requests periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            await self._cleanup_old_requests(current_time)
            self.last_cleanup = current_time
        
        # Check burst limit (requests per second)
        burst_window = 1  # 1 second window
        burst_requests = self.burst_requests[client_ip]
        
        # Remove requests older than burst window
        while burst_requests and burst_requests[0] < current_time - burst_window:
            burst_requests.popleft()
        
        if len(burst_requests) >= self.burst_limit:
            logger.warning(f"Burst rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": 1
                },
                headers={"Retry-After": "1"}
            )
        
        # Check rate limit (requests per minute)
        minute_window = 60  # 1 minute window
        requests = self.requests[client_ip]
        
        # Remove requests older than minute window
        while requests and requests[0] < current_time - minute_window:
            requests.popleft()
        
        if len(requests) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Add current request
        requests.append(current_time)
        burst_requests.append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check for forwarded headers (for reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    async def _cleanup_old_requests(self, current_time: float):
        """Clean up old request records"""
        cutoff_time = current_time - 300  # 5 minutes ago
        
        # Clean up minute-based requests
        for ip in list(self.requests.keys()):
            requests = self.requests[ip]
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            if not requests:
                del self.requests[ip]
        
        # Clean up burst requests
        for ip in list(self.burst_requests.keys()):
            burst_requests = self.burst_requests[ip]
            while burst_requests and burst_requests[0] < cutoff_time:
                burst_requests.popleft()
            
            if not burst_requests:
                del self.burst_requests[ip]


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for additional protection
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.blocked_ips = set()
        self.suspicious_ips = defaultdict(int)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        
        # Allow localhost requests for testing
        if client_ip in ['127.0.0.1', '::1', 'localhost']:
            return await call_next(request)
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={"error": "Access denied"}
            )
        
        # Check for suspicious patterns
        user_agent = request.headers.get("User-Agent", "").lower()
        if self._is_suspicious_request(request, user_agent):
            self.suspicious_ips[client_ip] += 1
            
            if self.suspicious_ips[client_ip] > 5:
                self.blocked_ips.add(client_ip)
                logger.warning(f"Blocked suspicious IP: {client_ip}")
                return JSONResponse(
                    status_code=403,
                    content={"error": "Access denied"}
                )
        
        response = await call_next(request)
        
        # Add additional security headers
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_suspicious_request(self, request: Request, user_agent: str) -> bool:
        """Check if request is suspicious"""
        # Check for common bot patterns
        bot_patterns = [
            "bot", "crawler", "spider", "scraper", "curl", "wget",
            "python-requests", "go-http-client", "java/", "okhttp"
        ]
        
        if any(pattern in user_agent for pattern in bot_patterns):
            return True
        
        # Check for suspicious paths
        suspicious_paths = [
            "/admin", "/wp-admin", "/.env", "/config", "/api/v1/admin",
            "/phpmyadmin", "/mysql", "/database"
        ]
        
        if any(path in request.url.path for path in suspicious_paths):
            return True
        
        # Check for SQL injection patterns
        sql_patterns = [
            "union select", "drop table", "delete from", "insert into",
            "update set", "or 1=1", "and 1=1"
        ]
        
        query_string = str(request.url.query).lower()
        if any(pattern in query_string for pattern in sql_patterns):
            return True
        
        return False


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {self._get_client_ip(request)}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Response: {response.status_code} "
            f"in {process_time:.3f}s for {request.method} {request.url.path}"
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
