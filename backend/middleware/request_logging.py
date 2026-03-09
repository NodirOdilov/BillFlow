"""
Request logging middleware for InvoiceForge.
Logs every incoming API request with timing, user, and response status.
"""

import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("invoiceforge.requests")


class RequestLoggingMiddleware(MiddlewareMixin):
    """Logs HTTP requests with timing, method, path, user, and status code."""

    SKIP_PATHS = {"/health/", "/api/schema/", "/static/", "/favicon.ico"}

    def process_request(self, request):
        request._start_time = time.monotonic()
        request._request_id = str(uuid.uuid4())[:8]
        return None

    def process_response(self, request, response):
        # Skip non-API paths and static assets
        if any(request.path.startswith(p) for p in self.SKIP_PATHS):
            return response

        elapsed_ms = 0.0
        if hasattr(request, "_start_time"):
            elapsed_ms = (time.monotonic() - request._start_time) * 1000

        request_id = getattr(request, "_request_id", "?")

        user_email = "anonymous"
        if hasattr(request, "user") and request.user.is_authenticated:
            user_email = request.user.email

        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": round(elapsed_ms, 2),
            "user": user_email,
            "ip": self._get_client_ip(request),
        }

        if response.status_code >= 500:
            logger.error("%(method)s %(path)s %(status)s [%(duration_ms)sms] user=%(user)s ip=%(ip)s rid=%(request_id)s", log_data)
        elif response.status_code >= 400:
            logger.warning("%(method)s %(path)s %(status)s [%(duration_ms)sms] user=%(user)s ip=%(ip)s rid=%(request_id)s", log_data)
        else:
            logger.info("%(method)s %(path)s %(status)s [%(duration_ms)sms] user=%(user)s ip=%(ip)s rid=%(request_id)s", log_data)

        # Attach request id to response headers for client-side tracing
        response["X-Request-ID"] = request_id

        return response

    @staticmethod
    def _get_client_ip(request):
        """Extract the client IP address from the request, respecting X-Forwarded-For."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
