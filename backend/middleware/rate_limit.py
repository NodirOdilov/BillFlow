"""
API rate limiting middleware for InvoiceForge.
Provides per-IP and per-user rate limiting using Django's cache framework.
"""

import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class APIRateLimitMiddleware(MiddlewareMixin):
    """
    Rate-limits API requests using a sliding window counter stored in cache.
    Limits are configurable via settings:
      - API_RATE_LIMIT_ANON: max requests per window for anonymous users (default 60)
      - API_RATE_LIMIT_AUTH: max requests per window for authenticated users (default 300)
      - API_RATE_LIMIT_WINDOW: window size in seconds (default 60)
    """

    def process_request(self, request):
        # Only rate-limit API endpoints
        if not request.path.startswith("/api/"):
            return None

        # Skip rate-limiting for admin and schema endpoints
        skip_paths = {"/api/schema/", "/api/docs/", "/api/redoc/"}
        if any(request.path.startswith(p) for p in skip_paths):
            return None

        window = getattr(settings, "API_RATE_LIMIT_WINDOW", 60)

        if hasattr(request, "user") and request.user.is_authenticated:
            limit = getattr(settings, "API_RATE_LIMIT_AUTH", 300)
            cache_key = f"rate_limit:user:{request.user.id}"
        else:
            limit = getattr(settings, "API_RATE_LIMIT_ANON", 60)
            ip = self._get_client_ip(request)
            cache_key = f"rate_limit:ip:{ip}"

        # Sliding window counter
        current_time = int(time.time())
        window_key = f"{cache_key}:{current_time // window}"

        request_count = cache.get(window_key, 0)

        if request_count >= limit:
            retry_after = window - (current_time % window)
            return JsonResponse(
                {
                    "status_code": 429,
                    "errors": [
                        {
                            "field": None,
                            "message": "Rate limit exceeded. Please try again later.",
                        }
                    ],
                },
                status=429,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Increment counter
        cache.set(window_key, request_count + 1, timeout=window * 2)

        return None

    def process_response(self, request, response):
        # Add rate limit headers to all API responses
        if not request.path.startswith("/api/"):
            return response

        window = getattr(settings, "API_RATE_LIMIT_WINDOW", 60)

        if hasattr(request, "user") and request.user.is_authenticated:
            limit = getattr(settings, "API_RATE_LIMIT_AUTH", 300)
            cache_key = f"rate_limit:user:{request.user.id}"
        else:
            limit = getattr(settings, "API_RATE_LIMIT_ANON", 60)
            ip = self._get_client_ip(request)
            cache_key = f"rate_limit:ip:{ip}"

        current_time = int(time.time())
        window_key = f"{cache_key}:{current_time // window}"
        request_count = cache.get(window_key, 0)

        response["X-RateLimit-Limit"] = str(limit)
        response["X-RateLimit-Remaining"] = str(max(0, limit - request_count))

        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
